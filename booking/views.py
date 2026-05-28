from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingForm, RegistrationForm, RoomFilterForm
from .models import (
    BOOKING_CLOSE_HOUR,
    BOOKING_OPEN_HOUR,
    BOOKING_SLOT_MINUTES,
    Booking,
    Room,
)

TIMELINE_START_HOUR = BOOKING_OPEN_HOUR
TIMELINE_END_HOUR = BOOKING_CLOSE_HOUR
TIMELINE_SLOT_MINUTES = BOOKING_SLOT_MINUTES
NON_BLOCKING_STATUSES = [Booking.Status.REJECTED, Booking.Status.CANCELLED]


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


def _build_booking_slot_options(selected_date, bookings):
    timeline_start = datetime.combine(selected_date, time(hour=TIMELINE_START_HOUR))
    timeline_end = datetime.combine(selected_date, time(hour=TIMELINE_END_HOUR))
    slot_cursor = timeline_start
    slot_duration = timedelta(minutes=TIMELINE_SLOT_MINUTES)
    slot_options = []
    slot_index = 0

    while slot_cursor < timeline_end:
        next_cursor = slot_cursor + slot_duration
        blocking_booking = None
        for booking in bookings:
            booking_start = datetime.combine(selected_date, booking.start_time)
            booking_end = datetime.combine(selected_date, booking.end_time)
            if booking_start < next_cursor and booking_end > slot_cursor:
                blocking_booking = booking
                break

        slot_options.append(
            {
                "index": slot_index,
                "label": f"{slot_cursor:%H:%M} - {next_cursor:%H:%M}",
                "start": slot_cursor.strftime("%H:%M"),
                "end": next_cursor.strftime("%H:%M"),
                "is_available": blocking_booking is None,
                "status": blocking_booking.get_status_display() if blocking_booking else "Available",
            }
        )
        slot_cursor += timedelta(minutes=TIMELINE_SLOT_MINUTES)
        slot_index += 1

    return slot_options


def home(request):
    featured_rooms = Room.objects.all()[:3]
    recommended_rooms = _get_recommended_rooms(request.user)
    stats = {
        "room_count": Room.objects.count(),
        "pending_count": Booking.objects.filter(status=Booking.Status.PENDING).count(),
        "location_count": Room.objects.values("location").distinct().count(),
    }
    return render(
        request,
        "booking/home.html",
        {
            "featured_rooms": featured_rooms,
            "recommended_rooms": recommended_rooms,
            "stats": stats,
        },
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
        room.bookings.exclude(status__in=NON_BLOCKING_STATUSES)
        .filter(booking_date__gte=today)
        .order_by("booking_date", "start_time")
        .values_list("booking_date", flat=True)
        .first()
    )
    default_date = first_upcoming_booking_date or today
    selected_date = _parse_selected_date(request.GET.get("date"), default_date)
    daily_bookings = list(
        room.bookings.exclude(status__in=NON_BLOCKING_STATUSES)
        .filter(booking_date=selected_date)
        .order_by("start_time")
    )
    slots, time_labels = _build_room_timeline(selected_date, daily_bookings)
    available_slot_count = sum(1 for slot in slots if slot["state"] == "available")
    pending_slot_count = sum(1 for slot in slots if slot["state"] == "pending")
    approved_slot_count = sum(1 for slot in slots if slot["state"] == "approved")
    upcoming_bookings = (
        room.bookings.exclude(status__in=NON_BLOCKING_STATUSES)
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


def _get_recommended_rooms(user):
    if user.is_authenticated:
        recent_room_ids = (
            Booking.objects.filter(user=user)
            .values_list("room_id", flat=True)
            .distinct()[:3]
        )
        recent_rooms = list(Room.objects.filter(id__in=recent_room_ids))
        if recent_rooms:
            return recent_rooms

    busy_room_ids = (
        Booking.objects.exclude(status__in=NON_BLOCKING_STATUSES)
        .filter(booking_date__gte=timezone.localdate())
        .values_list("room_id", flat=True)
        .distinct()
    )
    return Room.objects.exclude(id__in=busy_room_ids)[:3] or Room.objects.all()[:3]


def register(request):
    if request.user.is_authenticated:
        return redirect("booking:profile")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. You can now book rooms with your profile.")
            return redirect("booking:room_list")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def profile(request):
    bookings = request.user.bookings.select_related("room").order_by("-booking_date", "-start_time")
    recent_bookings = list(bookings[:6])
    for booking in recent_bookings:
        booking.can_cancel_for_current_user = booking.can_be_cancelled_by(request.user)
    pending_count = bookings.filter(status=Booking.Status.PENDING).count()
    approved_count = bookings.filter(status=Booking.Status.APPROVED).count()
    rejected_count = bookings.filter(status=Booking.Status.REJECTED).count()
    cancelled_count = bookings.filter(status=Booking.Status.CANCELLED).count()

    return render(
        request,
        "booking/profile.html",
        {
            "bookings": recent_bookings,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "cancelled_count": cancelled_count,
        },
    )


@login_required
def booking_history(request):
    bookings = list(request.user.bookings.select_related("room").order_by("-booking_date", "-start_time"))
    for booking in bookings:
        booking.can_cancel_for_current_user = booking.can_be_cancelled_by(request.user)
    return render(request, "booking/booking_history.html", {"bookings": bookings})


@login_required
def booking_create(request, slug):
    room = get_object_or_404(Room, slug=slug)
    requested_date = _parse_selected_date(
        request.POST.get("booking_date") or request.GET.get("date"),
        timezone.localdate(),
    )
    daily_bookings = list(
        room.bookings.exclude(status__in=NON_BLOCKING_STATUSES)
        .filter(booking_date=requested_date)
        .order_by("start_time")
    )
    slot_options = _build_booking_slot_options(requested_date, daily_bookings)

    if request.method == "POST":
        form = BookingForm(request.POST, room=room, user=request.user)
        if form.is_valid():
            try:
                booking = form.save()
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                messages.success(request, "Booking request submitted for administrator review.")
                return redirect("booking:booking_confirmation", pk=booking.pk)
    else:
        form = BookingForm(room=room, user=request.user, initial={"booking_date": requested_date})

    return render(
        request,
        "booking/booking_form.html",
        {
            "form": form,
            "room": room,
            "today": timezone.localdate(),
            "selected_date": requested_date,
            "slot_options": slot_options,
        },
    )


@login_required
def booking_confirmation(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if not request.user.is_staff and booking.user_id != request.user.id:
        raise PermissionDenied("You can only view your own booking confirmations.")
    return render(
        request,
        "booking/booking_confirmation.html",
        {"booking": booking},
    )


@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if not request.user.is_staff and booking.user_id != request.user.id:
        raise PermissionDenied("You can only cancel your own bookings.")
    if request.method != "POST":
        return redirect("booking:booking_history")

    if booking.status == Booking.Status.CANCELLED:
        messages.info(request, "This booking has already been cancelled.")
    elif booking.status == Booking.Status.REJECTED:
        messages.info(request, "Rejected bookings do not need to be cancelled.")
    elif booking.has_started():
        messages.error(request, "Past bookings cannot be cancelled.")
    else:
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        messages.success(request, "Booking request cancelled successfully.")

    return redirect("booking:booking_history")


def about(request):
    recent_rooms = Room.objects.all()[:4]
    return render(request, "booking/about.html", {"recent_rooms": recent_rooms})
