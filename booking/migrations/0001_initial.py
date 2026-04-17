from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Room",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                (
                    "room_type",
                    models.CharField(
                        choices=[
                            ("conference", "Conference Room"),
                            ("studio", "Studio"),
                            ("hall", "Event Hall"),
                            ("classroom", "Classroom"),
                            ("outdoor", "Outdoor Space"),
                        ],
                        max_length=20,
                    ),
                ),
                ("capacity", models.PositiveIntegerField()),
                ("location", models.CharField(max_length=180)),
                ("short_description", models.CharField(max_length=220)),
                ("description", models.TextField()),
                ("image_url", models.URLField(blank=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("booking_date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("purpose", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="booking.room",
                    ),
                ),
            ],
            options={"ordering": ["-booking_date", "-start_time"]},
        ),
    ]
