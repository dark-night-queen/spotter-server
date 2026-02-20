from rest_framework.serializers import ModelSerializer
from apps.trip.models import Trip, ELDLog, TimeLog


class TimeLogSerializer(ModelSerializer):
    class Meta:
        model = TimeLog
        fields = ["status", "start_time", "end_time", "location_text", "remarks"]


class ELDLogSerializer(ModelSerializer):
    status_changes = TimeLogSerializer(many=True, read_only=True)

    class Meta:
        model = ELDLog
        fields = ["date", "total_miles", "status_changes"]


class TripDetailSerializer(ModelSerializer):
    daily_logs = ELDLogSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = "__all__"


class TripListSerializer(ModelSerializer):
    """Simplified version for the list view"""

    class Meta:
        model = Trip
        fields = [
            "id",
            "current_location",
            "pickup_location",
            "dropoff_location",
            "created_at",
        ]
