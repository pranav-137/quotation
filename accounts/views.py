import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EmailForm, OTPForm
from .models import EmailOTP, User

RESEND_GAP_SECONDS = 60

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _finish_login(request, email, method):
    """Create the user on first sign-in (this is where the email gets saved), then log in."""
    email = email.strip().lower()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = User.objects.create_user(email=email, signup_method=method)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("quotes:maker")


def _login_context(form):
    return {"form": form, "google_enabled": bool(settings.GOOGLE_CLIENT_ID)}


# ---------------- Email + OTP ----------------
def request_code(request):
    if request.user.is_authenticated:
        return redirect("quotes:maker")

    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        recently_sent = EmailOTP.objects.filter(
            email=email, created_at__gte=timezone.now() - timedelta(seconds=RESEND_GAP_SECONDS)
        ).exists()
        if recently_sent:
            form.add_error(None, "A code was just sent. Please wait a minute before requesting another.")
        else:
            code = f"{secrets.randbelow(10**6):06d}"
            EmailOTP.objects.filter(email=email).delete()
            EmailOTP.objects.create(email=email, code_hash=make_password(code))
            try:
                send_mail(
                    subject="Your Quotation Maker sign-in code",
                    message=(
                        f"Your sign-in code is {code}.\n\n"
                        f"It is valid for {EmailOTP.TTL_MINUTES} minutes. "
                        "If you did not request this, you can ignore this email."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                )
            except Exception:
                EmailOTP.objects.filter(email=email).delete()
                form.add_error(None, "We couldn't send the email right now. Please try again in a moment.")
                return render(request, "accounts/login.html", _login_context(form))
            request.session["otp_email"] = email
            return redirect("accounts:verify")

    return render(request, "accounts/login.html", _login_context(form))


def verify_code(request):
    email = request.session.get("otp_email")
    if not email:
        return redirect("accounts:login")

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp = EmailOTP.objects.filter(email=email).first()
        if not otp or otp.is_expired:
            form.add_error(None, "This code has expired. Please request a new one.")
        elif otp.attempts >= EmailOTP.MAX_ATTEMPTS:
            form.add_error(None, "Too many wrong attempts. Please request a new code.")
        else:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            if check_password(form.cleaned_data["code"], otp.code_hash):
                EmailOTP.objects.filter(email=email).delete()
                request.session.pop("otp_email", None)
                return _finish_login(request, email, "email")
            form.add_error("code", "Incorrect code.")

    return render(request, "accounts/verify.html", {"form": form, "email": email})


# ---------------- Google ----------------
def _google_redirect_uri(request):
    return settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(reverse("accounts:google_callback"))


def google_login(request):
    if not settings.GOOGLE_CLIENT_ID:
        messages.error(request, "Google sign-in is not configured.")
        return redirect("accounts:login")
    state = secrets.token_urlsafe(24)
    request.session["google_state"] = state
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


def google_callback(request):
    expected_state = request.session.pop("google_state", None)
    if request.GET.get("error"):
        messages.error(request, "Google sign-in was cancelled.")
        return redirect("accounts:login")
    if not expected_state or request.GET.get("state") != expected_state or not request.GET.get("code"):
        messages.error(request, "Google sign-in failed (invalid state). Please try again.")
        return redirect("accounts:login")

    try:
        token = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": request.GET["code"],
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": _google_redirect_uri(request),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token.raise_for_status()
        info = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token.json()['access_token']}"},
            timeout=10,
        )
        info.raise_for_status()
        info = info.json()
    except (requests.RequestException, KeyError, ValueError):
        messages.error(request, "Could not complete Google sign-in. Please try again.")
        return redirect("accounts:login")

    email = (info.get("email") or "").strip()
    if not email or not info.get("email_verified"):
        messages.error(request, "Your Google account has no verified email address.")
        return redirect("accounts:login")

    return _finish_login(request, email, "google")


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("quotes:home")
