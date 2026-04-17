from django.contrib import admin

from .models import Booking, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "room_type", "capacity", "location")
    list_filter = ("room_type", "location")
    search_fields = ("name", "location", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.action(description="Mark selected bookings as approved")
def approve_bookings(modeladmin, request, queryset):
    queryset.update(status=Booking.Status.APPROVED)


@admin.action(description="Mark selected bookings as rejected")
def reject_bookings(modeladmin, request, queryset):
    queryset.update(status=Booking.Status.REJECTED)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "room",
        "full_name",
        "booking_date",
        "start_time",
        "end_time",
        "status",
    )
    list_filter = ("status", "booking_date", "room")
    search_fields = ("full_name", "email", "room__name", "purpose")
    date_hierarchy = "booking_date"
    actions = [approve_bookings, reject_bookings]


admin.site.site_header = "SpaceFlow Admin"
admin.site.site_title = "SpaceFlow Admin Portal"
admin.site.index_title = "Booking Management Dashboard"
