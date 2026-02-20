from django.db import models
from apps.core.models import BaseModel
from apps.trip.constants import DriverStatus


class Trip(BaseModel):
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    initial_cycle_hours = models.FloatField(
        default=0.0, help_text="Hours used in the 70hr/8day cycle"
    )

    # metadata fields for ELD sheet
    driver_id = models.TextField(max_length=255, blank=True)
    vehicle_id = models.TextField(max_length=255, blank=True)
    trailer_id = models.TextField(max_length=255, blank=True)

    def __str__(self):
        return f"Trip for {self.driver} from {self.pickup_location} to {self.dropoff_location}"


class ELDLog(BaseModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="daily_logs")
    date = models.DateField()

    # metadata fields for ELD sheet
    total_miles = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("trip", "date")
        ordering = ["date"]


class TimeLog(BaseModel):
    eld_log = models.ForeignKey(
        ELDLog, on_delete=models.CASCADE, related_name="status_changes"
    )
    status = models.CharField(max_length=15, choices=DriverStatus.choices)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    # metadata fields for ELD sheet
    location_text = models.CharField(max_length=255)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["start_time"]
