from datetime import time

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    BOOKING_CLOSE_HOUR,
    BOOKING_OPEN_HOUR,
    BOOKING_SLOT_MINUTES,
    Booking,
    Room,
)


class RoomFilterForm(forms.Form):
    room_type = forms.ChoiceField(
        choices=[("", "All room types"), *Room.RoomType.choices],
        required=False,
    )
    capacity = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={"placeholder": "Minimum capacity"}),
    )


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"placeholder": "name@example.com"}))
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Last name"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.setdefault("placeholder", "Choose a username")
        self.fields["password1"].widget.attrs.setdefault("placeholder", "Create a password")
        self.fields["password2"].widget.attrs.setdefault("placeholder", "Confirm password")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
        return user


class BookingForm(forms.ModelForm):
    booking_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "hidden"}),
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "hidden"}),
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "hidden"}),
    )

    class Meta:
        model = Booking
        fields = [
            "booking_date",
            "start_time",
            "end_time",
            "purpose",
        ]
        widgets = {
            "purpose": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Describe your event or activity"}
            ),
        }

    def __init__(self, *args, room=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room
        self.user = user
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def _user_display_name(self):
        if self.user is None or not self.user.is_authenticated:
            return ""
        return self.user.get_full_name() or self.user.username

    def _user_email(self):
        if self.user is None or not self.user.is_authenticated:
            return ""
        return self.user.email

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.room is not None:
            instance.room = self.room
        if self.user is not None and self.user.is_authenticated:
            instance.user = self.user
            instance.full_name = self._user_display_name()
            instance.email = self._user_email()
        if commit:
            with transaction.atomic():
                list(
                    Booking.objects.select_for_update().filter(
                        room=instance.room,
                        booking_date=instance.booking_date,
                    )
                )
                instance.full_clean()
                instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        if self.errors or self.room is None:
            return cleaned_data

        if not self._user_email():
            raise forms.ValidationError("Your account needs an email address before you can submit a booking.")

        booking_date = cleaned_data.get("booking_date")
        if booking_date and booking_date < timezone.localdate():
            self.add_error("booking_date", "Booking date must be today or later.")

        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        open_time = time(BOOKING_OPEN_HOUR, 0)
        close_time = time(BOOKING_CLOSE_HOUR, 0)

        if start_time and start_time.minute % BOOKING_SLOT_MINUTES != 0:
            self.add_error("start_time", "Start time must use a 30-minute interval.")
        if end_time and end_time.minute % BOOKING_SLOT_MINUTES != 0:
            self.add_error("end_time", "End time must use a 30-minute interval.")
        if start_time and start_time < open_time:
            self.add_error(
                "start_time",
                f"Bookings must start at or after {open_time.strftime('%H:%M')}.",
            )
        if end_time and end_time > close_time:
            self.add_error(
                "end_time",
                f"Bookings must end at or before {close_time.strftime('%H:%M')}.",
            )
        if start_time and end_time:
            duration_minutes = (
                end_time.hour * 60
                + end_time.minute
                - start_time.hour * 60
                - start_time.minute
            )
            if duration_minutes < BOOKING_SLOT_MINUTES:
                self.add_error("end_time", "Please select at least one 30-minute slot.")

        if start_time and booking_date and booking_date == timezone.localdate():
            if start_time <= timezone.localtime().time():
                self.add_error("start_time", "Start time cannot be in the past.")

        if self.errors:
            return cleaned_data

        candidate = Booking(
            user=self.user if self.user and self.user.is_authenticated else None,
            room=self.room,
            full_name=self._user_display_name(),
            email=self._user_email(),
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            purpose=cleaned_data.get("purpose", ""),
        )

        try:
            candidate.clean()
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

        return cleaned_data
