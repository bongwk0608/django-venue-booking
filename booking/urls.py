from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = "booking"

urlpatterns = [
    path("", views.home, name="home"),
    path("rooms/", views.room_list, name="room_list"),
    path("rooms/<slug:slug>/", views.room_detail, name="room_detail"),
    path("rooms/<slug:slug>/book/", views.booking_create, name="booking_create"),
    path("bookings/<int:pk>/confirmation/", views.booking_confirmation, name="booking_confirmation"),
    path("bookings/", views.booking_history, name="booking_history"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/profile/", views.profile, name="profile"),
    path("about/", views.about, name="about"),
]
