from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


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
            self.slug = slugify(self.name)
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
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be later than start time.")

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
