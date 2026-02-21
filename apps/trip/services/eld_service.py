from datetime import date, timedelta

from loguru import logger

from django.utils import timezone

from apps.trip.constants import DriverStatus
from apps.trip.models import ELDLog, TimeLog, Trip
from apps.trip.services.geo_service import GeoService

AVERAGE_SPEED_MPH = 60  # Used for mileage calculations when not provided
TOTAL_SECONDS_IN_DAY = 24 * 3600

ON_DUTY_CYCLE_LIMIT = 70  # hours in 8-day cycle
ON_DUTY_HOURS_LIMIT = 14  # hours of on-duty allowed in a day
DRIVING_HOURS_LIMIT = 11  # hours of driving allowed in a day
DRIVING_BEFORE_BREAK_LIMIT = 8  # hours of driving before a 30 min break
DAILY_RESET_HOURS = 10  # hours of rest for a daily reset (sleeper berth)
FUEL_MILEAGE_LIMIT = 1000  # miles before a fueling stop is required


class EldService:
    def __init__(
        self, trip_id: int, on_duty_cycle_limit: int = ON_DUTY_CYCLE_LIMIT
    ) -> None:
        self.trip = Trip.objects.get(id=trip_id)
        # Ensure we start at a clean datetime
        self.current_time = self.trip.created_at

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

    def _seconds_until_midnight(self, dt: timezone):
        start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_passed = (dt - start_of_day).total_seconds()
        return TOTAL_SECONDS_IN_DAY - seconds_passed

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

    def simulate_driving(self, total_distance, avg_speed=AVERAGE_SPEED_MPH):
        logger.info(
            f"Simulating driving for Trip ID: {self.trip.id} - Total Distance: {total_distance} miles at Avg Speed: {avg_speed} mph"
        )
        self.distance_remaining = total_distance

        while self.distance_remaining > 0:
            # 1. Determine constraints
            logger.info(
                f"Current Time: {self.current_time}, Distance Remaining: {self.distance_remaining} miles, Driving Hrs Today: {self.driving_hrs_today}, Break Clock: {self.break_clock_driving}, Cycle Hrs Remaining: {self.cycle_hrs_remaining}"
            )
            drive_left = DRIVING_HOURS_LIMIT - self.driving_hrs_today

            # 14-hour window is: 14 - (time elapsed since day started)
            elapsed_today = (
                self.current_time - self.day_start_time
            ).total_seconds() / 3600
            window_left = max(0, ON_DUTY_HOURS_LIMIT - elapsed_today)

            break_left = DRIVING_BEFORE_BREAK_LIMIT - self.break_clock_driving
            fuel_left = (FUEL_MILEAGE_LIMIT - self.miles_since_fueling) / avg_speed

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
                        DriverStatus.SLEEPER_BERTH,
                        DAILY_RESET_HOURS,
                        remarks="10hr Daily Reset",
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
            if self.miles_since_fueling >= FUEL_MILEAGE_LIMIT:
                self.add_log_entry(DriverStatus.ON_DUTY, 0.5, remarks="Fueling Stop")
                self.miles_since_fueling = 0

    def generate_trip(self, route_data):
        logger.info(
            f"Generating trip logs for Trip ID: {self.trip.id} with route data: {route_data}"
        )

        logger.info(f"Adding pre-trip inspection log for Trip ID: {self.trip.id}")
        self.add_log_entry(DriverStatus.ON_DUTY, 0.25, remarks="Pre-trip Inspection")

        logger.info(f"Simulating drive to pickup location for Trip ID: {self.trip.id}")
        self.simulate_driving(route_data["to_pickup_miles"])

        logger.info(f"Adding loading log for Trip ID: {self.trip.id}")
        self.add_log_entry(DriverStatus.ON_DUTY, 1.0, remarks="Loading Freight")

        logger.info(f"Simulating drive to dropoff location for Trip ID: {self.trip.id}")
        self.simulate_driving(route_data["to_dropoff_miles"])

        logger.info(f"Adding unloading log for Trip ID: {self.trip.id}")
        self.add_log_entry(DriverStatus.ON_DUTY, 1.0, remarks="Unloading Freight")

        logger.info(f"Adding post-trip inspection log for Trip ID: {self.trip.id}")
        self.add_log_entry(DriverStatus.ON_DUTY, 0.25, remarks="Post-trip Inspection")

    def generate_full_trip(self):
        logger.info(f"Generating full trip for Trip ID: {self.trip.id}")
        route_data = GeoService.get_route_data(
            self.trip.current_location,
            self.trip.pickup_location,
            self.trip.dropoff_location,
        )
        self.trip.route_geometry = route_data["geometry"]
        self.trip.save()
        self.generate_trip(route_data["metrics"])
