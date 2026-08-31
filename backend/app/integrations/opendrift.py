from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Protocol, Optional
import math
import logging
from app.schemas.scene import GeoJSONPolygon

logger = logging.getLogger(__name__)

class DriftAdapterProtocol(Protocol):
    async def run_hindcast(self, incident_id: str, slick_polygon: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        ...
    async def run_forecast(self, incident_id: str, slick_polygon: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        ...

class FixtureDriftAdapter:
    """Fixture drift adapter simulating particle drift backward and forward in time."""
    async def run_hindcast(self, incident_id: str, slick_polygon: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        # Centroid of mock slick is around (76.11, 9.82)
        # We simulate a wind/current that pushes northeast, meaning it originated southwest: (75.98, 9.72)
        origin_lon, origin_lat = 75.98, 9.72

        origin_pt = {
            "type": "Point",
            "coordinates": [origin_lon, origin_lat]
        }

        # Origin probability cone
        probability_cone = {
            "type": "Polygon",
            "coordinates": [[
                [origin_lon - 0.05, origin_lat - 0.05],
                [origin_lon + 0.05, origin_lat - 0.05],
                [origin_lon + 0.08, origin_lat + 0.05],
                [origin_lon - 0.08, origin_lat + 0.05],
                [origin_lon - 0.05, origin_lat - 0.05]
            ]]
        }

        # Hindcast path from origin to current position
        hindcast_path = {
            "type": "LineString",
            "coordinates": [
                [origin_lon, origin_lat],
                [origin_lon + 0.04, origin_lat + 0.03],
                [origin_lon + 0.08, origin_lat + 0.07],
                [76.11, 9.82]
            ]
        }

        return {
            "origin_point": origin_pt,
            "origin_probability_cone": probability_cone,
            "origin_time_estimate": timestamp - timedelta(hours=18),
            "origin_confidence": 0.72,
            "hindcast_path": hindcast_path,
            "forward_path": None
        }

    async def run_forecast(self, incident_id: str, slick_polygon: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        # Current centroid is (76.11, 9.82), we forecast drift northeast up to (76.25, 9.95)
        forward_path = {
            "type": "LineString",
            "coordinates": [
                [76.11, 9.82],
                [76.16, 9.86],
                [76.21, 9.91],
                [76.25, 9.95]
            ]
        }

        return {
            "origin_point": None,
            "origin_probability_cone": None,
            "origin_time_estimate": None,
            "origin_confidence": None,
            "hindcast_path": None,
            "forward_path": forward_path
        }

class OpenDriftAdapter:
    """
    OpenDrift-based drift adapter for particle drift simulation.

    For MVP, this uses simplified physics but follows the OpenDrift interface.
    In production, this would integrate with the actual OpenDrift library.
    """

    def __init__(self):
        # In a real implementation, we would initialize OpenDrift models here
        self._initialized = False
        logger.info("OpenDriftAdapter initialized (using simplified physics for MVP)")

    async def _initialize_opendrift(self):
        """Initialize OpenDrift models - placeholder for actual implementation."""
        # TODO: Replace with actual OpenDrift initialization when environment allows
        # For now, we'll use simplified calculations
        if not self._initialized:
            logger.info("OpenDrift models initialized (simplified)")
            self._initialized = True

    async def run_hindcast(self, incident_id: str, slick_polygon: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        """
        Calculate hindcast trajectory and probable origin point/time.

        Args:
            incident_id: ID of the incident
            slick_polygon: GeoJSON polygon of the oil slick
            timestamp: Timestamp of the slick observation

        Returns:
            Dictionary containing hindcast results:
            {
                "origin_point": GeoJSON Point,
                "origin_probability_cone": GeoJSON Polygon,
                "origin_time_estimate": datetime,
                "origin_confidence": float (0-1),
                "hindcast_path": GeoJSON LineString,
                "forward_path": None
            }
        """
        await self._initialize_opendrift()

        # Extract centroid from slick polygon for calculations
        # In a real implementation, we would use proper geometric calculations
        coords = slick_polygon.get("coordinates", [[[0, 0]]])[0]  # Exterior ring

        # Calculate centroid (simplified - average of coordinates)
        if coords and len(coords) > 0:
            lons = [pt[0] for pt in coords]
            lats = [pt[1] for pt in coords]
            centroid_lon = sum(lons) / len(lons)
            centroid_lat = sum(lats) / len(lats)
        else:
            # Default fallback
            centroid_lon, centroid_lat = 76.11, 9.82

        # Simulate drift based on typical wind/current patterns in the region
        # For MVP, we use a simplified backwards drift model
        # In production, this would be replaced with actual OpenDrift simulation

        # Simulate a typical drift pattern: oil generally drifts with wind/current
        # We'll assume the slick drifted northeast to reach current position
        # Therefore, origin is southwest of current position

        # Drift parameters (would be configurable based on environmental data)
        drift_speed_knots = 2.0  # knots
        drift_hours = 18.0  # hours back in time
        drift_direction_deg = 45.0  # Northeast direction (from origin to slick)

        # Convert drift to degrees (approximate)
        # 1 nautical mile ≈ 1/60 degree latitude
        # 1 knot = 1 nautical mile/hour
        drift_distance_nm = drift_speed_knots * drift_hours
        drift_distance_deg_lat = drift_distance_nm / 60.0

        # For longitude, adjust by cosine of latitude
        drift_distance_deg_lon = drift_distance_nm / (60.0 * math.cos(math.radians(centroid_lat)))

        # Calculate origin point (drift backwards from slick position)
        origin_lon = centroid_lon - (drift_distance_deg_lon * math.cos(math.radians(drift_direction_deg)))
        origin_lat = centroid_lat - (drift_distance_deg_lat * math.sin(math.radians(drift_direction_deg)))

        # Origin point
        origin_pt = {
            "type": "Point",
            "coordinates": [origin_lon, origin_lat]
        }

        # Origin probability cone (uncertainty increases with time)
        # Cone size increases with hindcast time
        uncertainty_radius = min(0.1, drift_hours / 50.0)  # Cap at ~0.1 degrees

        probability_cone = {
            "type": "Polygon",
            "coordinates": [[
                [origin_lon - uncertainty_radius, origin_lat - uncertainty_radius],
                [origin_lon + uncertainty_radius, origin_lat - uncertainty_radius],
                [origin_lon + uncertainty_radius * 1.5, origin_lat + uncertainty_radius],
                [origin_lon - uncertainty_radius * 1.5, origin_lat + uncertainty_radius],
                [origin_lon - uncertainty_radius, origin_lat - uncertainty_radius]
            ]]
        }

        # Hindcast path from origin to current position
        # Create a simple path illustrating the drift trajectory
        hindcast_path = {
            "type": "LineString",
            "coordinates": [
                [origin_lon, origin_lat],
                [origin_lon + (drift_distance_deg_lon * 0.33), origin_lat + (drift_distance_deg_lat * 0.33)],
                [origin_lon + (drift_distance_deg_lon * 0.66), origin_lat + (drift_distance_deg_lat * 0.66)],
                [centroid_lon, centroid_lat]
            ]
        }

        # Origin confidence decreases with hindcast time and uncertainty
        origin_confidence = max(0.3, min(0.9, 1.0 - (drift_hours / 48.0)))

        return {
            "origin_point": origin_pt,
            "origin_probability_cone": probability_cone,
            "origin_time_estimate": timestamp - timedelta(hours=drift_hours),
            "origin_confidence": round(origin_confidence, 2),
            "hindcast_path": hindcast_path,
            "forward_path": None
        }

    async def run_forecast(self, incident_id: str, slick_polygon: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        """
        Calculate forecast trajectory for the slick's future movement.

        Args:
            incident_id: ID of the incident
            slick_polygon: GeoJSON polygon of the oil slick
            timestamp: Timestamp of the slick observation

        Returns:
            Dictionary containing forecast results:
            {
                "origin_point": None,
                "origin_probability_cone": None,
                "origin_time_estimate": None,
                "origin_confidence": None,
                "hindcast_path": None,
                "forward_path": GeoJSON LineString
            }
        """
        await self._initialize_opendrift()

        # Extract centroid from slick polygon for calculations
        coords = slick_polygon.get("coordinates", [[[0, 0]]])[0]  # Exterior ring

        # Calculate centroid (simplified - average of coordinates)
        if coords and len(coords) > 0:
            lons = [pt[0] for pt in coords]
            lats = [pt[1] for pt in coords]
            centroid_lon = sum(lons) / len(lons)
            centroid_lat = sum(lats) / len(lats)
        else:
            # Default fallback
            centroid_lon, centroid_lat = 76.11, 9.82

        # Forecast parameters
        forecast_speed_knots = 1.5  # knots (slightly slower due to spreading/dissipation)
        forecast_hours = 24.0  # hours ahead
        forecast_direction_deg = 45.0  # Continue northeast drift

        # Convert forecast to degrees
        forecast_distance_nm = forecast_speed_knots * forecast_hours
        forecast_distance_deg_lat = forecast_distance_nm / 60.0
        forecast_distance_deg_lon = forecast_distance_nm / (60.0 * math.cos(math.radians(centroid_lat)))

        # Calculate forecast endpoint
        forecast_lon = centroid_lon + (forecast_distance_deg_lon * math.cos(math.radians(forecast_direction_deg)))
        forecast_lat = centroid_lat + (forecast_distance_deg_lat * math.sin(math.radians(forecast_direction_deg)))

        # Forecast path
        forward_path = {
            "type": "LineString",
            "coordinates": [
                [centroid_lon, centroid_lat],
                [centroid_lon + (forecast_distance_deg_lon * 0.33), centroid_lat + (forecast_distance_deg_lat * 0.33)],
                [centroid_lon + (forecast_distance_deg_lon * 0.66), centroid_lat + (forecast_distance_deg_lat * 0.66)],
                [forecast_lon, forecast_lat]
            ]
        }

        return {
            "origin_point": None,
            "origin_probability_cone": None,
            "origin_time_estimate": None,
            "origin_confidence": None,
            "hindcast_path": None,
            "forward_path": forward_path
        }
