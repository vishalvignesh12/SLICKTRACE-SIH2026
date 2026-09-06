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


import httpx
import json
from typing import Dict, Any
from app.models.satellite_scene import SatelliteScene


# TODO: Implement actual ML provider implementations (e.g., REST client, gRPC client)
class RESTMLProvider(MLInferenceProvider):
    """REST-based ML provider."""

    def __init__(self, service_url: str, timeout_seconds: int = 30):
        self.service_url = service_url
        self.timeout_seconds = timeout_seconds

    async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
        """
        Call ML inference service via REST API.
        """
        try:
            # Prepare request payload based on satellite scene
            # This assumes the ML service expects certain fields from the scene
            payload = {
                "scene_id": str(scene.scene_id),
                "satellite_id": scene.satellite_id,
                "datetime": scene.datetime.isoformat() if scene.datetime else None,
                "geometry": {
                    "type": scene.geometry.type if scene.geometry else None,
                    "coordinates": scene.geometry.coordinates if scene.geometry else None
                },
                "cloud_cover": scene.cloud_cover,
                "product_type": scene.product_type,
                "image_url": scene.image_url  # Include image URL for ML inference
            }

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.service_url}/predict",
                    json=payload
                )
                response.raise_for_status()
                return response.json()

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

    if provider_type == "fixture":
        return FixtureMLProvider()
    elif provider_type == "rest":
        return RESTMLProvider(
            service_url=settings.ML_SERVICE_URL,
            timeout_seconds=settings.ML_INFERENCE_TIMEOUT_SECONDS
        )
    else:
        # Default to fixture for safety
        return FixtureMLProvider()