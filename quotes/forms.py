from datetime import timedelta
from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator, RegexValidator
from django.forms import formset_factory
from django.utils import timezone

GSTIN_VALIDATOR = RegexValidator(
    regex=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$",
    message="Enter a valid 15-character GSTIN (e.g. 22AAAAA0000A1Z5).",
)
GST_RATES = [(0, "0%"), (5, "5%"), (12, "12%"), (18, "18%"), (28, "28%")]
MAX_LOGO_BYTES = 1 * 1024 * 1024  # keep uploads small (serverless request-size limits)


def _today():
    return timezone.localdate()


class QuotationForm(forms.Form):
    # Company
    company_name = forms.CharField(max_length=200)
    company_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    company_gstin = forms.CharField(
        label="Company GSTIN", max_length=15, required=False, validators=[GSTIN_VALIDATOR],
        widget=forms.TextInput(attrs={"placeholder": "22AAAAA0000A1Z5", "style": "text-transform:uppercase"}),
    )
    company_logo = forms.ImageField(required=False)

    # Quotation
    estimate_number = forms.CharField(max_length=50, initial="EST-0001")
    date = forms.DateField(initial=_today, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    valid_till = forms.DateField(
        initial=lambda: _today() + timedelta(days=15),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    # Customer
    customer_name = forms.CharField(max_length=200)
    customer_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    customer_gstin = forms.CharField(
        label="Customer GSTIN (optional)", max_length=15, required=False, validators=[GSTIN_VALIDATOR],
        widget=forms.TextInput(attrs={"placeholder": "optional", "style": "text-transform:uppercase"}),
    )

    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    terms = forms.CharField(label="Terms & conditions", required=False, widget=forms.Textarea(attrs={"rows": 5}))
    signature = forms.ImageField(required=False,label="Authorized signature")

    def clean_company_gstin(self):
        return self.cleaned_data["company_gstin"].strip().upper()

    def clean_customer_gstin(self):
        return self.cleaned_data["customer_gstin"].strip().upper()

    def clean_company_logo(self):
        logo = self.cleaned_data.get("company_logo")
        if logo and logo.size > MAX_LOGO_BYTES:
            raise forms.ValidationError("Logo must be smaller than 1 MB.")
        return logo

    def clean(self):
        cleaned = super().clean()
        d, v = cleaned.get("date"), cleaned.get("valid_till")
        if d and v and v < d:
            self.add_error("valid_till", "Valid-till date cannot be before the quotation date.")
        return cleaned


class ItemForm(forms.Form):
    description = forms.CharField(max_length=300, widget=forms.TextInput(attrs={"placeholder": "Item / service"}))
    hsn_code = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"placeholder": "HSN/SAC"}))
    quantity = forms.DecimalField(
        max_digits=12, decimal_places=2, initial=1, validators=[MinValueValidator(Decimal("0.01"))],
        widget=forms.NumberInput(attrs={"class": "qty", "step": "0.01", "min": "0.01"}),
    )
    rate = forms.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        widget=forms.NumberInput(attrs={"class": "rate", "step": "0.01", "min": "0"}),
    )
    gst_applicable = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={"class": "gst-on"}))
    gst_percent = forms.TypedChoiceField(
        choices=GST_RATES, coerce=int, initial=18, widget=forms.Select(attrs={"class": "gst-pct"}),
    )


ItemFormSet = formset_factory(ItemForm, extra=1, can_delete=True)
class ContactForm(forms.Form):
    subject = forms.CharField(max_length=120)
    message = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 6}))