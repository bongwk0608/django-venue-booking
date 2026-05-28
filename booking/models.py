from datetime import time

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


BOOKING_OPEN_HOUR = 8
BOOKING_CLOSE_HOUR = 22
BOOKING_SLOT_MINUTES = 30


class Room(models.Model):
    class RoomType(models.TextChoices):
        CONFERENCE = "conference", "Conference Room"
        STUDIO = "studio", "Studio"
        HALL = "hall", "Event Hall"
        CLASSROOM = "classroom", "Classroom"
        OUTDOOR = "outdoor", "Outdoor Space"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=180)
    short_description = models.CharField(max_length=220)
    description = models.TextField()
    image_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "room"
            candidate = base
            counter = 2
            while Room.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("booking:room_detail", args=[self.slug])


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="bookings",
        null=True,
        blank=True,
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    purpose = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-booking_date", "-start_time"]

    def __str__(self) -> str:
        return f"{self.room.name} - {self.booking_date} ({self.full_name})"

    def starts_at(self):
        starts_at = timezone.datetime.combine(self.booking_date, self.start_time)
        return timezone.make_aware(starts_at, timezone.get_current_timezone())

    def has_started(self) -> bool:
        return self.starts_at() <= timezone.localtime()

    def can_be_cancelled_by(self, user) -> bool:
        if not user.is_authenticated:
            return False
        if not user.is_staff and self.user_id != user.id:
            return False
        if self.status in {Booking.Status.CANCELLED, Booking.Status.REJECTED}:
            return False
        return not self.has_started()

    def clean(self):
        errors = {}

        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors["end_time"] = "End time must be later than start time."

        open_time = time(BOOKING_OPEN_HOUR, 0)
        close_time = time(BOOKING_CLOSE_HOUR, 0)
        if self.start_time and self.start_time < open_time:
            errors.setdefault(
                "start_time",
                f"Bookings must start at or after {open_time.strftime('%H:%M')}.",
            )
        if self.end_time and self.end_time > close_time:
            errors.setdefault(
                "end_time",
                f"Bookings must end at or before {close_time.strftime('%H:%M')}.",
            )

        if self.start_time and self.start_time.minute % BOOKING_SLOT_MINUTES != 0:
            errors.setdefault("start_time", "Start time must align with a 30-minute slot.")
        if self.end_time and self.end_time.minute % BOOKING_SLOT_MINUTES != 0:
            errors.setdefault("end_time", "End time must align with a 30-minute slot.")

        if self.booking_date and self.start_time:
            if self.starts_at() < timezone.localtime():
                errors.setdefault("start_time", "Booking start time cannot be in the past.")

        if errors:
            raise ValidationError(errors)

        if not all([self.room_id, self.booking_date, self.start_time, self.end_time]):
            return

        overlapping = Booking.objects.filter(
            room=self.room,
            booking_date=self.booking_date,
        ).exclude(pk=self.pk)

        overlapping = overlapping.filter(
            ~Q(status__in=[Booking.Status.REJECTED, Booking.Status.CANCELLED]),
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        )

        if overlapping.exists():
            raise ValidationError(
                "This time slot is already occupied. Please choose another time."
            )
