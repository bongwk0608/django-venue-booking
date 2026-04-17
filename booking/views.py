from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingForm, RoomFilterForm
from .models import Booking, Room

TIMELINE_START_HOUR = 8
TIMELINE_END_HOUR = 22
TIMELINE_SLOT_MINUTES = 30


def _parse_selected_date(raw_date, fallback_date):
    if not raw_date:
        return fallback_date
    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return fallback_date


def _build_room_timeline(selected_date, bookings):
    timeline_start = datetime.combine(selected_date, time(hour=TIMELINE_START_HOUR))
    timeline_end = datetime.combine(selected_date, time(hour=TIMELINE_END_HOUR))
    slot_cursor = timeline_start
    slots = []
    time_labels = []

    while slot_cursor < timeline_end:
        next_cursor = slot_cursor + timedelta(minutes=TIMELINE_SLOT_MINUTES)
        overlapping_booking = None
        for booking in bookings:
            booking_start = datetime.combine(selected_date, booking.start_time)
            booking_end = datetime.combine(selected_date, booking.end_time)
            if booking_start < next_cursor and booking_end > slot_cursor:
                overlapping_booking = booking
                break

        slot_state = "available"
        tooltip = f"{slot_cursor:%H:%M} - {next_cursor:%H:%M}: Available"
        if overlapping_booking:
            slot_state = (
                "pending"
                if overlapping_booking.status == Booking.Status.PENDING
                else "approved"
            )
            tooltip = (
                f"{slot_cursor:%H:%M} - {next_cursor:%H:%M}: "
                f"{overlapping_booking.get_status_display()}"
            )

        slots.append(
            {
                "state": slot_state,
                "tooltip": tooltip,
            }
        )

        if slot_cursor.minute == 0:
            time_labels.append({"label": slot_cursor.strftime("%H:%M"), "span": 2})

        slot_cursor = next_cursor

    return slots, time_labels


def home(request):
    featured_rooms = Room.objects.all()[:3]
    stats = {
        "room_count": Room.objects.count(),
        "pending_count": Booking.objects.filter(status=Booking.Status.PENDING).count(),
        "location_count": Room.objects.values("location").distinct().count(),
    }
    return render(
        request,
        "booking/home.html",
        {"featured_rooms": featured_rooms, "stats": stats},
    )


def room_list(request):
    rooms = Room.objects.all()
    filter_form = RoomFilterForm(request.GET or None)

    if filter_form.is_valid():
        room_type = filter_form.cleaned_data.get("room_type")
        capacity = filter_form.cleaned_data.get("capacity")
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        if capacity:
            rooms = rooms.filter(capacity__gte=capacity)

    return render(
        request,
        "booking/room_list.html",
        {
            "rooms": rooms,
            "filter_form": filter_form,
        },
    )


def room_detail(request, slug):
    room = get_object_or_404(Room, slug=slug)
    today = timezone.localdate()
    first_upcoming_booking_date = (
        room.bookings.exclude(status=Booking.Status.REJECTED)
        .filter(booking_date__gte=today)
        .order_by("booking_date", "start_time")
        .values_list("booking_date", flat=True)
        .first()
    )
    default_date = first_upcoming_booking_date or today
    selected_date = _parse_selected_date(request.GET.get("date"), default_date)
    daily_bookings = list(
        room.bookings.exclude(status=Booking.Status.REJECTED)
        .filter(booking_date=selected_date)
        .order_by("start_time")
    )
    slots, time_labels = _build_room_timeline(selected_date, daily_bookings)
    available_slot_count = sum(1 for slot in slots if slot["state"] == "available")
    pending_slot_count = sum(1 for slot in slots if slot["state"] == "pending")
    approved_slot_count = sum(1 for slot in slots if slot["state"] == "approved")
    upcoming_bookings = (
        room.bookings.exclude(status=Booking.Status.REJECTED)
        .filter(booking_date__gte=selected_date)
        .order_by("booking_date", "start_time")[:5]
    )

    return render(
        request,
        "booking/room_detail.html",
        {
            "room": room,
            "selected_date": selected_date,
            "previous_date": selected_date - timedelta(days=1),
            "next_date": selected_date + timedelta(days=1),
            "slots": slots,
            "time_labels": time_labels,
            "daily_bookings": daily_bookings,
            "available_slot_count": available_slot_count,
            "pending_slot_count": pending_slot_count,
            "approved_slot_count": approved_slot_count,
            "upcoming_bookings": upcoming_bookings,
        },
    )


def booking_create(request, slug):
    room = get_object_or_404(Room, slug=slug)
    requested_date = _parse_selected_date(request.GET.get("date"), timezone.localdate())

    if request.method == "POST":
        form = BookingForm(request.POST, room=room)
        if form.is_valid():
            booking = form.save()
            return redirect("booking:booking_confirmation", pk=booking.pk)
    else:
        form = BookingForm(room=room, initial={"booking_date": requested_date})

    return render(
        request,
        "booking/booking_form.html",
        {
            "form": form,
            "room": room,
            "today": timezone.localdate(),
        },
    )


def booking_confirmation(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(
        request,
        "booking/booking_confirmation.html",
        {"booking": booking},
    )


def about(request):
    recent_rooms = Room.objects.all()[:4]
    return render(request, "booking/about.html", {"recent_rooms": recent_rooms})
