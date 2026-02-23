# Spotter: Real-Time Logistics Tracker

A Django-based simulation engine for tracking truck movements between US landmarks.

## 🚀 Tech Stack

Backend: Django 5.x / Python 3.13

Infrastructure: Render (Web Service)

Database: Supabase PostgreSQL (via Session Pooler)

Static Files: WhiteNoise

## 🚛 The Simulation Engine

This project features a custom movement simulation designed for Ideal Conditions.

Constant Velocity: 60 km/h.

Logic: Real-time ETA and distance-to-destination updates.

Environment: Tested on Manhattan-based land routes (Times Square to Central Park).

## 🛠️ Infrastructure Wins

High Availability: Configured to use the Supabase Session Pooler (Port 5432) to ensure stable IPv4 connectivity on Render's network.

Production-Ready: Gunicorn-ready with WhiteNoise integration for high-performance static asset delivery.

## 🏁 Getting Started

* **Install uv:** This project uses `uv` for extremely fast dependency management.
* **Install Dependencies:** ```uv sync```
* Activate virtual env (created by uv) to access packages & run django commands.
  ```bash
  source path/to/.venv/bin/activate
  ```
* Start server locally:
  ```bash
  python manage.py runserver
  ```
