from loguru import logger
import requests


class GeoService:
    @staticmethod
    def get_coords(address):
        """Convert address text to coordinates using Nominatim (Free)"""
        url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
        headers = {"User-Agent": "EldApp-Assessment"}
        response = requests.get(url, headers=headers).json()
        if response:
            return response[0]["lon"], response[0]["lat"]
        return None

    @classmethod
    def get_route_data(cls, current, pickup, dropoff):
        logger.info(f"Fetching route data for Current: {current}, Pickup: {pickup}, Dropoff: {dropoff}")
        curr_lon, curr_lat = cls.get_coords(current)
        pick_lon, pick_lat = cls.get_coords(pickup)
        drop_lon, drop_lat = cls.get_coords(dropoff)

        logger.info(f"Fetching Leg 1 (Current to Pickup) from OSRM: {curr_lon},{curr_lat} to {pick_lon},{pick_lat}")
        leg1 = cls._fetch_osrm(curr_lon, curr_lat, pick_lon, pick_lat)

        logger.info(f"Fetching Leg 2 (Pickup to Dropoff) from OSRM: {pick_lon},{pick_lat} to {drop_lon},{drop_lat}")
        leg2 = cls._fetch_osrm(pick_lon, pick_lat, drop_lon, drop_lat)

        return {
            "to_pickup_miles": leg1["distance"] * 0.000621371,  
            "to_dropoff_miles": leg2["distance"] * 0.000621371,
            "total_duration_hrs": (leg1["duration"] + leg2["duration"]) / 3600,
        }

    @staticmethod
    def _fetch_osrm(lon1, lat1, lon2, lat2):
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        return requests.get(url).json()["routes"][0]
