from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.request_code, name="login"),
    path("verify/", views.verify_code, name="verify"),
    path("google/", views.google_login, name="google_login"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("logout/", views.logout_view, name="logout"),
]
