from django.db import models

from apps.core.models import BaseModel
from apps.trip.constants import DriverStatus


class Trip(BaseModel):
    start_address = models.CharField(max_length=255)
    pickup_address = models.CharField(max_length=255)
    drop_off_address = models.CharField(max_length=255)
    initial_cycle_hours = models.FloatField(
        default=0.0, help_text="Hours used in the 70hr/8day cycle"
    )

    # metadata fields for ELD sheet
    driver_id = models.TextField(max_length=255, blank=True, default="DVI-0001")
    vehicle_id = models.TextField(max_length=255, blank=True, default="VHI-0001")
    trailer_id = models.TextField(max_length=255, blank=True, default="TLI-0001")
    metrics = models.JSONField(null=True, blank=True)
    route_geometry = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Trip for {self.driver_id} from {self.pickup_address} to {self.drop_off_address}"


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
