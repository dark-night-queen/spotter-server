from datetime import datetime, time, timedelta, date
from apps.trip.constants import DriverStatus
from apps.trip.models import ELDLog, TimeLog, Trip
from apps.trip.services.geo_service import GeoService


class EldService:
    def __init__(self, trip_id: int, on_duty_cycle_limit: int = 70) -> None:
        self.trip = Trip.objects.get(id=trip_id)
        # Ensure we start at a clean datetime
        self.current_time = self.trip.created_at or datetime.now()

        # State tracking
        self.distance_remaining = 0
        self.miles_since_fueling = 0

        # HOS Clocks
        self.driving_hrs_today = 0  # Max 11
        self.day_start_time = self.current_time
        self.break_clock_driving = 0  # Max 8 hrs of driving before 30m break
        self.cycle_hrs_remaining = on_duty_cycle_limit - self.trip.initial_cycle_hours

    def _get_or_create_eld_log(self, log_date: date):
        log, _ = ELDLog.objects.get_or_create(trip=self.trip, date=log_date)
        return log

    def _seconds_until_midnight(self, dt: datetime):
        tomorrow = dt.date() + timedelta(days=1)
        midnight = datetime.combine(tomorrow, time(0, 0))
        return (midnight - dt).total_seconds()

    def _create_record(self, status, hours, location, remarks):
        log_date = self.current_time.date()
        eld_log = self._get_or_create_eld_log(log_date)

        end_time = self.current_time + timedelta(hours=hours)

        TimeLog.objects.create(
            eld_log=eld_log,
            status=status,
            start_time=self.current_time,
            end_time=end_time,
            location_text=location,
            remarks=remarks,
        )

        # Track miles per daily log sheet
        if status == DriverStatus.DRIVING:
            # We assume a standard speed for mileage calculation if not provided
            miles = hours * 60
            eld_log.total_miles = (eld_log.total_miles or 0) + miles
            eld_log.save()
            self.driving_hrs_today += hours
            self.break_clock_driving += hours

        # Cycle tracking (On-Duty and Driving reduce the 70hr/8day bucket)
        if status in [DriverStatus.DRIVING, DriverStatus.ON_DUTY]:
            self.cycle_hrs_remaining -= hours

        self.current_time = end_time

    def add_log_entry(self, status, duration_hours, location="", remarks=""):
        """Recursively handles splits across one or more midnights."""
        if duration_hours <= 0:
            return

        seconds_until_midnight = self._seconds_until_midnight(self.current_time)
        hours_until_midnight = seconds_until_midnight / 3600

        if duration_hours > hours_until_midnight:
            # Fill the rest of today
            self._create_record(status, hours_until_midnight, location, remarks)

            # Reset daily clocks for the brand new day
            self.driving_hrs_today = 0
            self.day_start_time = self.current_time  # Now 00:00 of the new day
            self.break_clock_driving = (
                0  # Breaks are reset by 10hr sleep, but logic handles it
            )

            # Recurse for the remaining time (handles multi-day rests)
            self.add_log_entry(
                status, duration_hours - hours_until_midnight, location, remarks
            )
        else:
            self._create_record(status, duration_hours, location, remarks)

    def simulate_driving(self, total_distance, avg_speed=60):
        self.distance_remaining = total_distance

        while self.distance_remaining > 0:
            # 1. Determine constraints
            drive_left = 11 - self.driving_hrs_today

            # 14-hour window is: 14 - (time elapsed since day started)
            elapsed_today = (
                self.current_time - self.day_start_time
            ).total_seconds() / 3600
            window_left = max(0, 14 - elapsed_today)

            break_left = 8 - self.break_clock_driving
            fuel_left = (1000 - self.miles_since_fueling) / avg_speed

            # How much can we drive before we hit ANY limit?
            can_drive_hours = min(drive_left, window_left, fuel_left, break_left)

            if can_drive_hours <= 0:
                if break_left <= 0:
                    # After 8 hours of driving, need 30 min break
                    self.add_log_entry(
                        DriverStatus.OFF_DUTY, 0.5, remarks="30min Rest Break"
                    )
                    self.break_clock_driving = 0
                else:
                    # Hit 11hr drive limit or 14hr window: Must take 10hr reset
                    self.add_log_entry(
                        DriverStatus.SLEEPER_BERTH, 10, remarks="10hr Daily Reset"
                    )
                continue

            # 2. Drive
            hours_to_reach_dest = self.distance_remaining / avg_speed
            actual_drive_hours = min(can_drive_hours, hours_to_reach_dest)

            distance_covered = actual_drive_hours * avg_speed
            self.add_log_entry(DriverStatus.DRIVING, actual_drive_hours)

            self.distance_remaining -= distance_covered
            self.miles_since_fueling += distance_covered

            # 3. Handle specific triggers
            if self.miles_since_fueling >= 1000:
                self.add_log_entry(DriverStatus.ON_DUTY, 0.5, remarks="Fueling Stop")
                self.miles_since_fueling = 0

    def generate_trip(self, route_data):
        # 1. Pre-Trip
        self.add_log_entry(DriverStatus.ON_DUTY, 0.25, remarks="Pre-trip Inspection")

        # 2. Current to Pickup
        self.simulate_driving(route_data["to_pickup_miles"])

        # 3. Loading (1 Hour) - Counts against 14hr window
        self.add_log_entry(DriverStatus.ON_DUTY, 1.0, remarks="Loading Freight")

        # 4. Pickup to Delivery
        self.simulate_driving(route_data["to_dropoff_miles"])

        # 5. Dropoff (1 Hour)
        self.add_log_entry(DriverStatus.ON_DUTY, 1.0, remarks="Unloading Freight")

        # 6. Final Inspection
        self.add_log_entry(DriverStatus.ON_DUTY, 0.25, remarks="Post-trip Inspection")

    def generate_full_trip(self):
        route_data = GeoService.get_route_data(
            self.trip.current_location,
            self.trip.pickup_location,
            self.trip.dropoff_location,
        )
        self.generate_trip(route_data)
