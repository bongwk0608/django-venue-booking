from django import forms
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

    def __init__(self, *args, room=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.room is not None:
            instance.room = self.room
        if commit:
            instance.full_clean()
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        if self.errors or self.room is None:
            return cleaned_data

        candidate = Booking(
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
