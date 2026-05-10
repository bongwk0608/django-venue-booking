from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Booking, Room


class BookingModelTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(
            name="Test Classroom",
            room_type=Room.RoomType.CLASSROOM,
            capacity=30,
            location="Block B",
            short_description="A test room.",
            description="A classroom used for automated tests.",
        )

    def test_end_time_must_be_after_start_time(self):
        booking = Booking(
            room=self.room,
            full_name="Student One",
            email="student@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(9, 0),
            purpose="Tutorial",
        )

        with self.assertRaises(ValidationError):
            booking.clean()

    def test_overlapping_non_rejected_booking_is_blocked(self):
        Booking.objects.create(
            room=self.room,
            full_name="Student One",
            email="student@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Tutorial",
            status=Booking.Status.APPROVED,
        )
        booking = Booking(
            room=self.room,
            full_name="Student Two",
            email="student2@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 30),
            end_time=time(11, 30),
            purpose="Workshop",
        )

        with self.assertRaises(ValidationError):
            booking.clean()

    def test_rejected_booking_does_not_block_slot(self):
        Booking.objects.create(
            room=self.room,
            full_name="Student One",
            email="student@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Tutorial",
            status=Booking.Status.REJECTED,
        )
        booking = Booking(
            room=self.room,
            full_name="Student Two",
            email="student2@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 30),
            end_time=time(11, 30),
            purpose="Workshop",
        )

        booking.clean()


class BookingAuthViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass12345",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass12345",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.room = Room.objects.create(
            name="Demo Hall",
            room_type=Room.RoomType.HALL,
            capacity=80,
            location="Main Building",
            short_description="A demo hall.",
            description="A hall used for view tests.",
        )

    def test_anonymous_user_can_browse_rooms(self):
        response = self.client.get(reverse("booking:room_list"))

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_when_booking(self):
        response = self.client.get(reverse("booking:booking_create", args=[self.room.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("booking:login"), response["Location"])

    def test_authenticated_user_can_create_booking(self):
        self.client.login(username="student", password="pass12345")
        response = self.client.post(
            reverse("booking:booking_create", args=[self.room.slug]),
            {
                "full_name": "Student",
                "email": "student@example.com",
                "booking_date": "2026-05-12",
                "start_time": "10:00",
                "end_time": "11:00",
                "purpose": "Group study",
            },
        )

        booking = Booking.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.user, self.user)

    def test_user_cannot_view_another_users_confirmation(self):
        booking = Booking.objects.create(
            user=self.other_user,
            room=self.room,
            full_name="Other",
            email="other@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Workshop",
        )
        self.client.login(username="student", password="pass12345")

        response = self.client.get(reverse("booking:booking_confirmation", args=[booking.pk]))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_any_booking_confirmation(self):
        booking = Booking.objects.create(
            user=self.other_user,
            room=self.room,
            full_name="Other",
            email="other@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Workshop",
        )
        self.client.login(username="staff", password="pass12345")

        response = self.client.get(reverse("booking:booking_confirmation", args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
