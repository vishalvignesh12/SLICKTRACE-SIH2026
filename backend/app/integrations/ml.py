"""
ML Inference Provider Abstraction
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Protocol
from datetime import datetime
from uuid import UUID

from app.models.satellite_scene import SatelliteScene


class MLProviderProtocol(Protocol):
    """Protocol defining the interface for ML inference providers."""
    async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
        ...


class MLInferenceProvider(ABC):
    """Abstract base class for ML inference providers."""

    @abstractmethod
    async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
        """
        Submit a satellite scene to ML inference and receive a prediction.

        Args:
            scene: Satellite scene to analyze

        Returns:
            Dictionary containing ML prediction following the PRD contract:
            {
                "detected": bool,
                "confidence": float (0-1),
                "area_km2": float,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[float, float]]]
                },
                "model_name": str,
                "model_version": str
            }
        """
        pass


class FixtureMLProvider(MLInferenceProvider):
    """Fixture ML provider for development and testing."""

    async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
        """
        Return a deterministic mock response based on the scene_id.
        This mimics the behavior of the existing FixtureSatelliteAdapter
        but returns data in the PRD ML output contract format.
        """
        # Deterministic mock based on scene_id hash
        scene_id_str = str(scene.scene_id)
        scene_hash = hash(scene_id_str) % 10000
        is_low_conf = "low" in scene_id_str.lower()

        confidence = 0.45 if is_low_conf else 0.94
        area_km2 = 12.43 if not is_low_conf else 4.21
        model_version = "fixture-v1"
        model_name = "oilspill-detector"

        # Mock geometry representing a typical slick
        mock_polygon = {
            "type": "Polygon",
            "coordinates": [[
                [76.10, 9.80],
                [76.12, 9.81],
                [76.15, 9.85],
                [76.13, 9.86],
                [76.09, 9.82],
                [76.10, 9.80]  # Closed polygon
            ]]
        }

        # Determine length, width, orientation based on scene ID (for consistency with tests)
        is_low_conf = "low" in scene_id_str.lower()
        length_km = 8.21 if not is_low_conf else 4.10
        width_km = 1.42 if not is_low_conf else 0.71
        orientation_deg = 73.0 if not is_low_conf else 45.0
        age_estimate_hours = 18.0 if not is_low_conf else 24.0
        age_conf = "HIGH" if not is_low_conf else "LOW"

        return {
            "detected": True,
            "confidence": confidence,
            "area_km2": area_km2,
            "geometry": mock_polygon,
            "model_name": model_name,
            "model_version": model_version,
            "length_km": length_km,
            "width_km": width_km,
            "orientation_deg": orientation_deg,
            "age_estimate_hours": age_estimate_hours,
            "age_confidence": age_conf
        }


import math
import numpy as np
import httpx
from typing import Dict, Any, List, Optional
from shapely.geometry import shape

from app.models.satellite_scene import SatelliteScene


def translate_ml_response(raw_resp: Dict[str, Any], scene: SatelliteScene) -> Dict[str, Any]:
    """
    Translate raw ML inference service response (PredictionResult.to_dict())
    into the standard backend ML contract.

    Args:
        raw_resp: Raw dictionary returned by ML service /predict endpoint
        scene: Source SatelliteScene analyzed

    Returns:
        Standardized dictionary complying with backend ML prediction contract
    """
    detected = bool(raw_resp.get("presence", raw_resp.get("detected", False)))
    raw_conf = raw_resp.get("max_confidence", raw_resp.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, float(raw_conf)))
    model_name = raw_resp.get("model_name", "oilspill-unet")
    model_version = str(raw_resp.get("model_version", "oilspill-unet-v1"))

    # Extract present or available regions
    raw_regions = raw_resp.get("present_regions") or raw_resp.get("regions") or []
    if not raw_regions and detected:
        raw_regions = raw_resp.get("likely_regions", [])

    total_area_m2 = 0.0
    spill_regions_converted: List[Dict[str, Any]] = []
    primary_geometry: Optional[Dict[str, Any]] = None

    for i, reg in enumerate(raw_regions):
        # Choose EPSG:4326 geographic polygon if available, else pixel polygon
        geo_geom = reg.get("polygon_geojson_geo") or reg.get("polygon_geojson_pixel")
        if primary_geometry is None and geo_geom:
            primary_geometry = geo_geom

        area_m2 = float(reg.get("area_m2_approx") or (reg.get("area_px2", 0.0) * 100.0))
        total_area_m2 += area_m2

        centroid_geo = reg.get("centroid_geo")
        centroid_dict = (
            {"lat": float(centroid_geo[1]), "lon": float(centroid_geo[0])}
            if centroid_geo and len(centroid_geo) == 2
            else {"lat": 0.0, "lon": 0.0}
        )

        spill_regions_converted.append({
            "region_id": f"reg_{scene.scene_id}_{i+1}",
            "confidence": confidence,
            "area_m2": area_m2,
            "geometry": geo_geom,
            "centroid": centroid_dict,
            "mask_uri": reg.get("mask_uri"),
            "prediction_uri": reg.get("prediction_uri")
        })

    # If no detected polygon was found, provide valid placeholder polygon ring
    if not primary_geometry:
        primary_geometry = {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]]
        }

    area_km2 = round(total_area_m2 / 1_000_000.0, 6) if detected else 0.0

    # Calculate slick characterization if geometry is valid
    length_km = None
    width_km = None
    orientation_deg = None
    if detected and primary_geometry:
        try:
            geom_shape = shape(primary_geometry)
            if not geom_shape.is_empty and geom_shape.area > 0:
                minx, miny, maxx, maxy = geom_shape.bounds
                lat_mid = (miny + maxy) / 2.0
                km_per_deg_lat = 111.0
                km_per_deg_lon = max(0.1, 111.0 * math.cos(math.radians(lat_mid)))
                dx_km = abs(maxx - minx) * km_per_deg_lon
                dy_km = abs(maxy - miny) * km_per_deg_lat
                length_km = round(float(math.sqrt(dx_km**2 + dy_km**2)), 3)
                width_km = round(float(min(dx_km, dy_km) if min(dx_km, dy_km) > 0 else length_km / 3.0), 3)
                orientation_deg = round(float(math.degrees(math.atan2(dy_km, max(0.001, dx_km)))), 1)
        except Exception:
            pass

    return {
        "detected": detected,
        "confidence": confidence,
        "area_km2": area_km2,
        "geometry": primary_geometry,
        "model_name": model_name,
        "model_version": model_version,
        "length_km": length_km,
        "width_km": width_km,
        "orientation_deg": orientation_deg,
        "age_estimate_hours": 12.0 if detected else None,
        "age_confidence": "MEDIUM" if detected else None,
        "spill_regions": spill_regions_converted
    }


class RESTMLProvider(MLInferenceProvider):
    """REST-based ML provider for invoking external ML inference service."""

    def __init__(self, service_url: str, timeout_seconds: int = 30):
        self.service_url = service_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
        """
        Call ML inference service via REST API and translate response.
        """
        try:
            image_uri = scene.image_url or f"storage://incoming/{scene.scene_id}.tif"
            acq_time = (
                scene.acquisition_time.isoformat()
                if hasattr(scene, "acquisition_time") and scene.acquisition_time
                else None
            )

            payload = {
                "scene_id": str(scene.scene_id),
                "image_uri": str(image_uri),
                "acquisition_time": acq_time,
                "threshold": 0.5
            }

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.service_url}/predict",
                    json=payload
                )
                response.raise_for_status()
                raw_json = response.json()
                return translate_ml_response(raw_json, scene)

        except httpx.TimeoutException:
            raise Exception(f"ML service request timed out after {self.timeout_seconds} seconds")
        except httpx.HTTPStatusError as e:
            raise Exception(f"ML service returned error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to call ML service: {str(e)}")


def get_ml_provider() -> MLInferenceProvider:
    """
    Factory function to get the configured ML provider.

    Returns:
        Configured MLInferenceProvider instance
    """
    from app.core.config import settings

    provider_type = settings.ML_PROVIDER.lower()

    if provider_type == "rest":
        return RESTMLProvider(
            service_url=settings.ML_SERVICE_URL,
            timeout_seconds=settings.ML_INFERENCE_TIMEOUT_SECONDS
        )
    else:
        # Default to fixture for safety
        return FixtureMLProvider()