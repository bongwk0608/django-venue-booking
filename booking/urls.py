from django.urls import path

from . import views


app_name = "booking"

urlpatterns = [
    path("", views.home, name="home"),
    path("rooms/", views.room_list, name="room_list"),
    path("rooms/<slug:slug>/", views.room_detail, name="room_detail"),
    path("rooms/<slug:slug>/book/", views.booking_create, name="booking_create"),
    path("bookings/<int:pk>/confirmation/", views.booking_confirmation, name="booking_confirmation"),
    path("about/", views.about, name="about"),
]
