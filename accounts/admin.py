import csv

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponse

from .models import User


@admin.action(description="Export selected emails to CSV")
def export_emails_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="user_emails.csv"'
    writer = csv.writer(response)
    writer.writerow(["email", "signed_up_via", "date_joined", "last_login"])
    for u in queryset.order_by("date_joined"):
        writer.writerow([u.email, u.signup_method, u.date_joined.isoformat(), u.last_login.isoformat() if u.last_login else ""])
    return response


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "signup_method", "date_joined", "last_login", "is_staff")
    list_filter = ("signup_method", "is_staff")
    search_fields = ("email",)
    actions = [export_emails_csv]
    fieldsets = (
        (None, {"fields": ("email", "password", "signup_method")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
