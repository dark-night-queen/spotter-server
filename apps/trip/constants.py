from django.db import models


class DriverStatus(models.TextChoices):
    OFF_DUTY = "OFF_DUTY", "Off Duty"
    SLEEPER_BERTH = "SLEEPER_BERTH", "Sleeper Berth"
    DRIVING = "DRIVING", "Driving"
    ON_DUTY = "ON_DUTY", "On Duty (not driving)"
