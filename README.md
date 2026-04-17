# SpaceFlow Booking Website

Simple Django-based room booking website with:

- User pages: home, room list, room detail, booking form, booking confirmation, about
- Admin pages: Django Admin login, dashboard, room management, booking management
- Booking conflict validation for occupied time slots

## Run locally

1. Install dependencies:
   `python3 -m pip install -r requirements.txt`
2. Apply migrations:
   `python3 manage.py migrate`
3. Create an admin user:
   `python3 manage.py createsuperuser`
4. Optional demo data:
   `python3 manage.py loaddata booking/fixtures/demo_rooms.json`
5. Start the server:
   `python3 manage.py runserver`

## Admin pages

- Admin login: `/admin/`
- Room management: `Room` model in Django Admin
- Booking management: `Booking` model in Django Admin

## Notes

- Room images use an `image_url` field to keep setup lightweight.
- Submitted bookings default to `Pending`.
- Time slot conflicts are blocked against pending and approved bookings.
