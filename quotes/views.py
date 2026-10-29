import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
import time
from django.conf import settings
from django.core.mail import EmailMessage
from .calc import Item, Quote
from .forms import ContactForm,ItemFormSet, QuotationForm
from .pdf import build_pdf


def home(request):
    """Public landing page."""
    return render(request, "quotes/home.html")


@login_required
def maker(request):
    """Fill in the form; on submit the PDF is generated and downloaded. Quotation data is not stored (only the owner's GSTIN)."""
    if request.method == "POST":
        form = QuotationForm(request.POST, request.FILES)
        formset = ItemFormSet(request.POST, prefix="items")
        if form.is_valid() and formset.is_valid():
            items = [
                Item(
                    description=f.cleaned_data["description"],
                    hsn_code=f.cleaned_data.get("hsn_code", ""),
                    quantity=f.cleaned_data["quantity"],
                    rate=f.cleaned_data["rate"],
                    gst_applicable=f.cleaned_data.get("gst_applicable", False),
                    gst_percent=f.cleaned_data["gst_percent"],
                )
                for f in formset.forms
                if f.cleaned_data and not f.cleaned_data.get("DELETE")
            ]
            if not items:
                messages.error(request, "Add at least one item to the quotation.")
            else:
                d = form.cleaned_data

                # ADDED (1): save the owner's GSTIN on their account
                if d["company_gstin"] and request.user.gstin != d["company_gstin"]:
                    request.user.gstin = d["company_gstin"]
                    request.user.save(update_fields=["gstin"])

                logo = d.get("company_logo")
                quote = Quote(
                    company_name=d["company_name"], company_address=d["company_address"],
                    company_gstin=d["company_gstin"], logo_bytes=logo.read() if logo else None,
                    estimate_number=d["estimate_number"].strip(), date=d["date"], valid_till=d["valid_till"],
                    customer_name=d["customer_name"], customer_address=d["customer_address"],
                    customer_gstin=d["customer_gstin"], notes=d["notes"], terms=d["terms"], items=items,
                )
                safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", quote.estimate_number)
                response = HttpResponse(build_pdf(quote), content_type="application/pdf")
                response["Content-Disposition"] = f'attachment; filename="Quotation_{safe}.pdf"'
                response.set_cookie("pdf_done", "1", max_age=60, samesite="Lax")   # <-- ADD THIS LINE
                return response
    else:
        # ADDED (2): pre-fill the form with the saved GSTIN
        form = QuotationForm(initial={"company_gstin": request.user.gstin})
        formset = ItemFormSet(prefix="items")
    return render(request, "quotes/maker.html", {"form": form, "formset": formset})
@login_required
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if time.time() - request.session.get("last_contact", 0) < 60:
            form.add_error(None, "Please wait a minute before sending another message.")
        else:
            try:
                EmailMessage(
                    subject=f"[Quotation Maker] {form.cleaned_data['subject']}",
                    body=f"From: {request.user.email}\n\n{form.cleaned_data['message']}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL],
                    reply_to=[request.user.email],
                ).send()
            except Exception:
                form.add_error(None, "Could not send your message right now. Please try again later.")
            else:
                request.session["last_contact"] = time.time()
                messages.success(request, "Thanks! Your message has been sent.")
                return redirect("quotes:contact")
    return render(request, "quotes/contact.html", {"form": form})