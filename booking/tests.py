from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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

    def test_cancelled_booking_does_not_block_slot(self):
        Booking.objects.create(
            room=self.room,
            full_name="Student One",
            email="student@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Tutorial",
            status=Booking.Status.CANCELLED,
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

    def test_has_started_uses_booking_start_datetime(self):
        future_start = timezone.localtime() + timedelta(days=1)
        future_booking = Booking(
            room=self.room,
            full_name="Student One",
            email="student@example.com",
            booking_date=future_start.date(),
            start_time=future_start.time().replace(second=0, microsecond=0),
            end_time=(future_start + timedelta(hours=1)).time().replace(second=0, microsecond=0),
            purpose="Tutorial",
        )
        past_start = timezone.localtime() - timedelta(days=1)
        past_booking = Booking(
            room=self.room,
            full_name="Student Two",
            email="student2@example.com",
            booking_date=past_start.date(),
            start_time=past_start.time().replace(second=0, microsecond=0),
            end_time=(past_start + timedelta(hours=1)).time().replace(second=0, microsecond=0),
            purpose="Tutorial",
        )

        self.assertFalse(future_booking.has_started())
        self.assertTrue(past_booking.has_started())


class BookingAuthViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student",
            email="student@example.com",
            first_name="Student",
            last_name="User",
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
                "booking_date": "2026-05-12",
                "start_time": "10:00",
                "end_time": "11:00",
                "purpose": "Group study",
            },
        )

        booking = Booking.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.full_name, "Student User")
        self.assertEqual(booking.email, "student@example.com")

    def test_booking_ignores_spoofed_name_and_email(self):
        self.client.login(username="student", password="pass12345")
        response = self.client.post(
            reverse("booking:booking_create", args=[self.room.slug]),
            {
                "full_name": "Fake Person",
                "email": "fake@example.com",
                "booking_date": "2026-05-12",
                "start_time": "10:00",
                "end_time": "11:00",
                "purpose": "Group study",
            },
        )

        booking = Booking.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.full_name, "Student User")
        self.assertEqual(booking.email, "student@example.com")

    def test_user_without_email_cannot_create_booking(self):
        no_email_user = User.objects.create_user(
            username="noemail",
            password="pass12345",
        )
        self.client.login(username="noemail", password="pass12345")
        response = self.client.post(
            reverse("booking:booking_create", args=[self.room.slug]),
            {
                "booking_date": "2026-05-12",
                "start_time": "10:00",
                "end_time": "11:00",
                "purpose": "Group study",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your account needs an email address")
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_rejects_minute_level_time(self):
        self.client.login(username="student", password="pass12345")
        response = self.client.post(
            reverse("booking:booking_create", args=[self.room.slug]),
            {
                "booking_date": "2026-05-12",
                "start_time": "09:10",
                "end_time": "10:00",
                "purpose": "Group study",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start time must use a 30-minute interval.")
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_rejects_duration_under_30_minutes(self):
        self.client.login(username="student", password="pass12345")
        response = self.client.post(
            reverse("booking:booking_create", args=[self.room.slug]),
            {
                "booking_date": "2026-05-12",
                "start_time": "09:00",
                "end_time": "09:00",
                "purpose": "Group study",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_form_shows_30_minute_slots(self):
        self.client.login(username="student", password="pass12345")

        response = self.client.get(
            f"{reverse('booking:booking_create', args=[self.room.slug])}?date=2026-05-12"
        )
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("08:00 - 08:30", content)
        self.assertIn('data-index="0"', content)
        self.assertIn('type="hidden"', content)
        self.assertIn("No time slot selected", content)
        self.assertNotIn('name="full_name"', content)
        self.assertNotIn('name="email"', content)

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

    def test_user_can_cancel_own_booking(self):
        booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            full_name="Student",
            email="student@example.com",
            booking_date=date(2026, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Workshop",
            status=Booking.Status.APPROVED,
        )
        self.client.login(username="student", password="pass12345")

        response = self.client.post(reverse("booking:booking_cancel", args=[booking.pk]))
        booking.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_user_cannot_cancel_past_booking(self):
        booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            full_name="Student",
            email="student@example.com",
            booking_date=date(2020, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Workshop",
            status=Booking.Status.APPROVED,
        )
        self.client.login(username="student", password="pass12345")

        response = self.client.post(reverse("booking:booking_cancel", args=[booking.pk]))
        booking.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.status, Booking.Status.APPROVED)

    def test_past_booking_does_not_show_cancel_button(self):
        Booking.objects.create(
            user=self.user,
            room=self.room,
            full_name="Student",
            email="student@example.com",
            booking_date=date(2020, 5, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Workshop",
            status=Booking.Status.APPROVED,
        )
        self.client.login(username="student", password="pass12345")

        response = self.client.get(reverse("booking:booking_history"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Cancel</button>")
        self.assertContains(response, "Past booking")

    def test_user_cannot_cancel_another_users_booking(self):
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

        response = self.client.post(reverse("booking:booking_cancel", args=[booking.pk]))
        booking.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(booking.status, Booking.Status.PENDING)
