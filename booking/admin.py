from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Booking, Room


ROOM_TYPE_PALETTE = {
    "conference": ("#0d3a56", "#d7e5ef"),
    "studio": ("#6b2c8a", "#efd6f5"),
    "hall": ("#a85731", "#ffe0d1"),
    "classroom": ("#1f6f45", "#dff4e6"),
    "outdoor": ("#2f6f93", "#d4e8f4"),
}

STATUS_PALETTE = {
    "pending": ("#a85731", "#ffe2d7"),
    "approved": ("#1f6f45", "#dff4e6"),
    "rejected": ("#a23232", "#ffe9e9"),
    "cancelled": ("#596977", "#e2e8f0"),
}


def _pill(label, color, bg):
    return format_html(
        '<span class="sf-pill" style="color:{};background:{};">{}</span>',
        color, bg, label,
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "room_type_pill", "capacity_display", "location")
    list_filter = ("room_type", "location")
    search_fields = ("name", "location", "description")
    prepopulated_fields = {"slug": ("name",)}
    save_on_top = True
    list_per_page = 25
    fieldsets = (
        ("Identity", {"fields": ("name", "slug", "room_type")}),
        ("Capacity & Location", {"fields": ("capacity", "location")}),
        ("Description", {"fields": ("short_description", "description", "image_url")}),
    )

    class Media:
        css = {"all": ("admin/css/spaceflow.css",)}

    @admin.display(description="Type", ordering="room_type")
    def room_type_pill(self, obj):
        color, bg = ROOM_TYPE_PALETTE.get(obj.room_type, ("#1e2a34", "#e2e8f0"))
        return _pill(obj.get_room_type_display(), color, bg)

    @admin.display(description="Capacity", ordering="capacity")
    def capacity_display(self, obj):
        return format_html('<span class="sf-mono">{} guests</span>', obj.capacity)


def _bulk_set_status(modeladmin, request, queryset, new_status, verb, level):
    queryset = queryset.exclude(status=new_status)
    changed = 0
    skipped = []
    with transaction.atomic():
        for booking in queryset.select_related("room"):
            booking.status = new_status
            if new_status == Booking.Status.APPROVED:
                try:
                    booking.full_clean()
                except ValidationError as exc:
                    skipped.append((booking, "; ".join(exc.messages)))
                    continue
            booking.save(update_fields=["status"])
            changed += 1

    if changed:
        modeladmin.message_user(request, f"{verb} {changed} booking(s).", level)
    if skipped:
        for booking, reason in skipped:
            modeladmin.message_user(
                request,
                f"Skipped “{booking}”: {reason}",
                messages.WARNING,
            )
    if not changed and not skipped:
        modeladmin.message_user(
            request,
            "No bookings needed this change.",
            messages.INFO,
        )


@admin.action(description="Approve selected bookings")
def approve_bookings(modeladmin, request, queryset):
    _bulk_set_status(modeladmin, request, queryset, Booking.Status.APPROVED, "Approved", messages.SUCCESS)


@admin.action(description="Reject selected bookings")
def reject_bookings(modeladmin, request, queryset):
    _bulk_set_status(modeladmin, request, queryset, Booking.Status.REJECTED, "Rejected", messages.WARNING)


@admin.action(description="Cancel selected bookings")
def cancel_bookings(modeladmin, request, queryset):
    _bulk_set_status(modeladmin, request, queryset, Booking.Status.CANCELLED, "Cancelled", messages.INFO)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "room_summary",
        "requester",
        "when_display",
        "status_badge",
        "row_actions",
    )
    list_display_links = ("room_summary", "requester", "when_display")
    list_filter = ("status", "booking_date", "room", "user__is_staff")
    search_fields = (
        "full_name", "email",
        "user__username", "user__email",
        "room__name", "purpose",
    )
    date_hierarchy = "booking_date"
    actions = [approve_bookings, reject_bookings, cancel_bookings]
    save_on_top = True
    list_per_page = 25
    list_select_related = ("room", "user")
    autocomplete_fields = ("room", "user")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Requester", {"fields": ("user", "full_name", "email")}),
        ("Room & Schedule", {"fields": ("room", "booking_date", "start_time", "end_time")}),
        ("Purpose", {"fields": ("purpose",)}),
        ("Decision", {"fields": ("status", "created_at")}),
    )

    class Media:
        css = {"all": ("admin/css/spaceflow.css",)}

    @admin.display(description="Room", ordering="room__name")
    def room_summary(self, obj):
        return format_html(
            '<span class="sf-room-link"><strong>{}</strong>'
            '<span class="sf-muted">{}</span></span>',
            obj.room.name, obj.room.location,
        )

    @admin.display(description="Requester", ordering="full_name")
    def requester(self, obj):
        return format_html(
            '<strong>{}</strong><span class="sf-muted">{}</span>',
            obj.full_name, obj.email,
        )

    @admin.display(description="When", ordering="booking_date")
    def when_display(self, obj):
        return format_html(
            '<strong>{}</strong><span class="sf-muted">{} – {}</span>',
            obj.booking_date.strftime("%a, %b %d, %Y"),
            obj.start_time.strftime("%H:%M"),
            obj.end_time.strftime("%H:%M"),
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        color, bg = STATUS_PALETTE.get(obj.status, ("#1e2a34", "#e2e8f0"))
        return _pill(obj.get_status_display(), color, bg)

    @admin.display(description="Quick actions")
    def row_actions(self, obj):
        choices = [
            (Booking.Status.APPROVED, "approve", "Approve", "sf-btn-approve"),
            (Booking.Status.REJECTED, "reject", "Reject", "sf-btn-reject"),
            (Booking.Status.CANCELLED, "cancel", "Cancel", "sf-btn-cancel"),
        ]

        buttons = []
        for skip_status, slug, label, klass in choices:
            if obj.status == skip_status:
                continue
            url = reverse(f"admin:booking_booking_{slug}", args=[obj.pk])
            buttons.append(format_html(
                '<button type="submit" class="sf-btn {}" '
                'formaction="{}" formmethod="post" formnovalidate>{}</button>',
                klass, url, label,
            ))

        if not buttons:
            return format_html('<span class="sf-muted">— no actions —</span>')
        return format_html('<div class="sf-actions">{}</div>', mark_safe("".join(buttons)))

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/approve/",
                self.admin_site.admin_view(self.handle_approve),
                name="booking_booking_approve",
            ),
            path(
                "<int:pk>/reject/",
                self.admin_site.admin_view(self.handle_reject),
                name="booking_booking_reject",
            ),
            path(
                "<int:pk>/cancel/",
                self.admin_site.admin_view(self.handle_cancel),
                name="booking_booking_cancel",
            ),
        ]
        return custom + urls

    def _set_status(self, request, pk, new_status, verb, level):
        if request.method != "POST":
            return redirect(reverse("admin:booking_booking_change", args=[pk]))

        try:
            with transaction.atomic():
                try:
                    booking = Booking.objects.select_related("room").get(pk=pk)
                except Booking.DoesNotExist:
                    raise Http404("Booking not found.")

                if booking.status == new_status:
                    self.message_user(
                        request,
                        f"“{booking}” is already {booking.get_status_display()}.",
                        messages.INFO,
                    )
                else:
                    booking.status = new_status
                    if new_status == Booking.Status.APPROVED:
                        booking.full_clean()
                    booking.save(update_fields=["status"])
                    self.message_user(request, f"{verb} “{booking}”.", level)
        except ValidationError as exc:
            self.message_user(
                request,
                f"Cannot {verb.lower()}: {'; '.join(exc.messages)}",
                messages.ERROR,
            )

        return redirect(
            request.META.get("HTTP_REFERER")
            or reverse("admin:booking_booking_changelist")
        )

    def handle_approve(self, request, pk):
        return self._set_status(request, pk, Booking.Status.APPROVED, "Approved", messages.SUCCESS)

    def handle_reject(self, request, pk):
        return self._set_status(request, pk, Booking.Status.REJECTED, "Rejected", messages.WARNING)

    def handle_cancel(self, request, pk):
        return self._set_status(request, pk, Booking.Status.CANCELLED, "Cancelled", messages.INFO)


admin.site.site_header = "SpaceFlow Admin"
admin.site.site_title = "SpaceFlow Admin Portal"
admin.site.index_title = "Booking Management Dashboard"
