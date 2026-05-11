# SpaceFlow - Venue Booking System

SpaceFlow is a Django-based room and facility booking system for a university framework project. It lets users browse rooms, check availability, register/login, submit booking requests, and track approval status. Staff manage rooms and approvals through Django Admin.

## Features

- Room browsing with type and capacity filters
- Room detail pages with availability timeline
- User registration, login, logout, sessions, and password hashing
- Authenticated booking requests linked to the logged-in user
- 30-minute interactive time-slot selection on the booking form
- User-side booking cancellation from My Bookings
- User profile and booking history
- Staff/admin management through Django Admin
- Booking conflict validation
- SQLite database for simple local and Docker demos
- Docker setup for consistent Windows/Mac environments

## Architecture

This project follows Django's MVC-style structure:

- `booking/models.py` is the data layer for rooms and bookings.
- `booking/views.py` handles request flow, business rules, and page context.
- `booking/templates/` and `templates/base.html` are the presentation layer.
- `booking/urls.py` and `venue_booking/urls.py` route browser requests to views.
- `booking/admin.py` configures Django Admin for staff management.

The project intentionally remains as one Django app, `booking`, because all features belong to the same facility-booking domain. For report and presentation purposes, the app is explained as functional modules: room browsing, booking, interactive time slots, availability checking, authentication, profile/history, admin management, recommendation, frontend UI/UX, navigation/MVC explanation, database, Docker/deployment, and testing.

## Database Choice

SQLite is intentionally kept for this university project. It is easy to run, requires no separate database server, works well for a single demo instance, and is fully supported by Django migrations.

PostgreSQL would be a reasonable future upgrade if the system needed multiple concurrent production users, advanced database operations, or deployment to a managed server environment. For the current project scope, adding PostgreSQL or MySQL would make setup more complex without improving the demo significantly.

## Run With Docker

Open Docker Desktop first and wait until the Docker engine is running.

```bash
docker-compose up --build
```

The Docker command runs migrations, loads demo rooms, and starts the Django development server.

Open:

```text
http://localhost:8000
```

Create an admin user in a second terminal:

```bash
docker-compose exec web python manage.py createsuperuser
```

Then open:

```text
http://localhost:8000/admin/
```

## Run Locally Without Docker

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata booking/fixtures/demo_rooms.json
python manage.py createsuperuser
python manage.py runserver
```

Open `http://localhost:8000`.

## Demo Script

1. Open the home page and explain the user/admin split.
2. Browse rooms and filter by type or capacity.
3. Open a room detail page and show the availability timeline.
4. Register a new user account.
5. Submit a booking request while logged in.
6. Select one or more consecutive 30-minute slots on the booking form.
7. Open My Bookings to show the user-specific booking history.
8. Cancel one booking from the user side if demonstrating withdrawal.
9. Login to Django Admin as staff.
10. Approve or reject the booking from the admin booking list.
11. Return to the user booking history and show the updated status.

## Team Review Workflow

- Each member should pull the latest GitHub version and run the system locally.
- Review related modules together, such as room browsing with recommendation, booking with availability/time slots, authentication with profile/history, admin with database, frontend with navigation/MVC, and Docker with testing.
- Write report sections only after the website behavior is stable, so the report does not become outdated.
- Make changes in a branch, test locally, push the branch, and merge only after group review.

## Troubleshooting

- If the room list is empty, run `python manage.py loaddata booking/fixtures/demo_rooms.json`.
- If login or booking routes fail after pulling changes, run `python manage.py migrate`.
- If port 8000 is already used, change the left side of the Docker port mapping, for example `"8001:8000"`.
- If local Python cannot import Django, run `pip install -r requirements.txt` inside the active virtual environment.
- If Docker Compose cannot connect to the Docker API, open Docker Desktop first.

## Environment Variables

- `DJANGO_SECRET_KEY`: overrides the development secret key.
- `DJANGO_DEBUG`: set to `False` outside development.
- `DJANGO_ALLOWED_HOSTS`: comma-separated host list, for example `localhost,127.0.0.1`.

## Future Scalability Suggestions

- Move from SQLite to PostgreSQL when deployment or concurrency needs justify it.
- Add email notifications for approval/rejection.
- Add a staff-facing dashboard only if Django Admin becomes insufficient.
- Add more room metadata such as equipment, building, and opening hours.
