from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Booking, Room


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
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    class Meta:
        model = Booking
        fields = [
            "full_name",
            "email",
            "booking_date",
            "start_time",
            "end_time",
            "purpose",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@example.com"}),
            "purpose": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Describe your event or activity"}
            ),
        }

    def __init__(self, *args, room=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room
        self.user = user
        if user and user.is_authenticated and not self.is_bound:
            display_name = user.get_full_name() or user.username
            self.fields["full_name"].initial = display_name
            self.fields["email"].initial = user.email
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.room is not None:
            instance.room = self.room
        if self.user is not None and self.user.is_authenticated:
            instance.user = self.user
        if commit:
            instance.full_clean()
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        if self.errors or self.room is None:
            return cleaned_data

        candidate = Booking(
            user=self.user if self.user and self.user.is_authenticated else None,
            room=self.room,
            full_name=cleaned_data.get("full_name", ""),
            email=cleaned_data.get("email", ""),
            booking_date=cleaned_data.get("booking_date"),
            start_time=cleaned_data.get("start_time"),
            end_time=cleaned_data.get("end_time"),
            purpose=cleaned_data.get("purpose", ""),
        )

        try:
            candidate.clean()
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

        return cleaned_data
