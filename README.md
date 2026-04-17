# SpaceFlow – Venue Booking System

## 🚀 Overview

SpaceFlow is a Django-based venue booking system that allows users to browse rooms and make reservations with conflict validation.

This project is fully containerized using Docker, ensuring consistent development and deployment environments.

---

## ✨ Features

* Browse available rooms
* View detailed room information
* Book rooms with date/time selection
* Prevent booking conflicts
* Admin dashboard for managing rooms and bookings

---

## 🛠 Tech Stack

* **Backend:** Django 4.x
* **Database:** SQLite (development)
* **Containerization:** Docker & Docker Compose
* **Server:** Django development server (upgrade to Gunicorn planned)

---

## 🐳 Run with Docker (Recommended)

```bash
docker-compose up --build
```

Visit:
http://localhost:8000

---

## 🧪 Run Locally (Without Docker)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## 🔐 Admin Access

* URL: `/admin/`
* Manage:

  * Rooms
  * Bookings

---

## 📌 Future Improvements

* PostgreSQL integration
* User authentication system
* Deployment (Render / AWS)
* Gunicorn + Nginx setup

---

## 💡 Key Highlights

* Dockerized environment for reproducibility
* Booking conflict detection logic
* Clean Django project structure
