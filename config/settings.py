import os
import urllib.parse
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-in-production")
if not DEBUG and SECRET_KEY == "dev-only-change-me-in-production":
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG=0")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS.append(".vercel.app")
if DEBUG:
    ALLOWED_HOSTS = ["*"]

# e.g. "https://your-app.vercel.app,https://yourdomain.com"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

if not DEBUG:
    # Vercel terminates HTTPS in front of Django
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "quotes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Production (Vercel): a Postgres database. Vercel sets DATABASE_URL when you add one.
# Local development falls back to SQLite.
if os.environ.get("DATABASE_URL"):
    _url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    _query = dict(urllib.parse.parse_qsl(_url.query))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _url.path.lstrip("/"),
            "USER": urllib.parse.unquote(_url.username or ""),
            "PASSWORD": urllib.parse.unquote(_url.password or ""),
            "HOST": _url.hostname,
            "PORT": _url.port or 5432,
            "OPTIONS": {"sslmode": _query.get("sslmode", "require")},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "quotes:maker"
LOGOUT_REDIRECT_URL = "quotes:home"

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # Vercel runs collectstatic for you when this is set

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Email (used to send the sign-in code) ----
# Development: codes are printed in the terminal running `runserver`.
# Production: set DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# and the EMAIL_* variables below.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_TIMEOUT = 15
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@quotemaker.local")

# ---- Google sign-in (OAuth 2.0). Leave empty to hide the "Continue with Google" button ----
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
# Optional: force the exact redirect URI instead of auto-detecting it
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL") or EMAIL_HOST_USER or "pranavkumar12384@gmail.com"