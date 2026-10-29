from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    """Users are identified by their email address (collected at sign-in)."""

    username = None
    email = models.EmailField("email address", unique=True)
    signup_method = models.CharField(max_length=10, blank=True, help_text="google or email")
    gstin = models.CharField("GSTIN", max_length=15, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class EmailOTP(models.Model):
    """One-time sign-in code sent by email. Only a hash of the code is stored."""

    TTL_MINUTES = 10
    MAX_ATTEMPTS = 5

    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=255)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=self.TTL_MINUTES)

    def __str__(self):
        return f"OTP for {self.email}"
