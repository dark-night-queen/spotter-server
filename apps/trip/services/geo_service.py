from googlemaps import Client as GoogleMapsClient
from loguru import logger

from django.conf import settings

METERS_TO_MILES = 0.000621371
SECONDS_TO_HOURS = 1 / 3600


class GeoService:
    client: GoogleMapsClient = GoogleMapsClient(key=settings.GOOGLE_MAPS_API_KEY)

    @classmethod
    def _fetch_google_route(cls, origin: str, destination: str):
        """Helper to fetch directions between two points"""
        try:
            result = cls.client.directions(origin, destination, mode="driving")

            if not result:
                return None

            route = result[0]["legs"][0]
            return {
                "distance_meters": route["distance"]["value"],
                "duration_seconds": route["duration"]["value"],
                "polyline": result[0]["overview_polyline"]["points"],
                "start_coords": route["start_location"],
                "end_coords": route["end_location"],
                "bounds": result[0]["bounds"],
            }
        except Exception as e:
            logger.error(f"Directions error: {e}")
            return None

    @classmethod
    def get_route_data(cls, current: str, pickup: str, drop_off: str):
        """
        Calculates trip metrics and geometry using Google Routes/Directions.
        """
        logger.info(f"Fetching route data: {current=} -> {pickup=} -> {drop_off=}")

        leg1 = cls._fetch_google_route(current, pickup)
        leg2 = cls._fetch_google_route(pickup, drop_off)

        if not leg1 or not leg2:
            raise ValueError("Routing service failed to calculate legs.")

        return {
            "metrics": {
                "to_pickup_miles": round(leg1["distance_meters"] * METERS_TO_MILES, 2),
                "to_drop_off_miles": round(
                    leg2["distance_meters"] * METERS_TO_MILES, 2
                ),
                "total_miles": round(
                    (leg1["distance_meters"] + leg2["distance_meters"])
                    * METERS_TO_MILES,
                    2,
                ),
                "total_duration_hrs": round(
                    (leg1["duration_seconds"] + leg2["duration_seconds"])
                    * SECONDS_TO_HOURS,
                    2,
                ),
                # Raw data for ELD Service "Actual Time" calculations
                "raw_seconds": leg1["duration_seconds"] + leg2["duration_seconds"],
                "raw_meters": leg1["distance_meters"] + leg2["distance_meters"],
            },
            "geometry": {
                "polyline": [leg1["polyline"], leg2["polyline"]],
                "start_coords": leg1["start_coords"],
                "pickup_coords": leg1["end_coords"],
                "drop_off_coords": leg2["end_coords"],
            },
        }
