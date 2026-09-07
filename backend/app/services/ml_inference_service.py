"""
ML Inference Service
Handles ML model invocation, timeout handling, and conversion to internal format.
"""
import time
import asyncio
from typing import Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ml import MLInferenceProvider, FixtureMLProvider, RESTMLProvider, get_ml_provider
from app.models.satellite_scene import SatelliteScene
from app.models.incident import Incident
from app.models.slick_detection import SlickDetection
from app.models.spill_region import SpillRegion
from app.core.config import settings
from app.core.logging import log_inference
from app.services.geospatial_service import GeospatialService
from geoalchemy2.shape import from_shape
from shapely.geometry import shape


def validate_ml_prediction(prediction: Dict[str, Any]) -> None:
    """
    Validate ML prediction against PRD contract and business rules.

    Args:
        prediction: ML prediction dictionary

    Raises:
        ValueError: If prediction is invalid
    """
    # Check required fields
    required_fields = ["detected", "confidence", "area_km2", "geometry", "model_name", "model_version"]
    for field in required_fields:
        if field not in prediction:
            raise ValueError(f"Missing required field in ML prediction: {field}")

    # Validate detected field
    if not isinstance(prediction["detected"], bool):
        raise ValueError("Field 'detected' must be a boolean")

    # Validate confidence
    confidence = prediction["confidence"]
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

    # Validate area_km2
    area_km2 = prediction["area_km2"]
    if not isinstance(area_km2, (int, float)) or area_km2 < 0:
        raise ValueError(f"Area must be non-negative, got {area_km2}")

    # Validate geometry
    geometry = prediction["geometry"]
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise ValueError("Geometry must be a GeoJSON Polygon")

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) == 0:
        raise ValueError("Geometry coordinates must be a non-empty list")

    # Validate coordinates structure (simplified validation)
    for ring in coordinates:
        if not isinstance(ring, list) or len(ring) < 4:
            raise ValueError("Each coordinate ring must be a list with at least 4 points")
        for point in ring:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("Each coordinate point must be a list of [longitude, latitude]")
            lon, lat = point
            if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                raise ValueError("Coordinate values must be numbers")
            # Basic range validation
            if not -180 <= lon <= 180:
                raise ValueError(f"Longitude out of range: {lon}")
            if not -90 <= lat <= 90:
                raise ValueError(f"Latitude out of range: {lat}")

    # Validate model fields
    if not isinstance(prediction["model_name"], str) or not prediction["model_name"].strip():
        raise ValueError("Model name must be a non-empty string")

    if not isinstance(prediction["model_version"], str) or not prediction["model_version"].strip():
        raise ValueError("Model version must be a non-empty string")


def convert_ml_to_detection_format(
    ml_prediction: Dict[str, Any],
    scene: SatelliteScene,
    processing_time_ms: int
) -> Dict[str, Any]:
    """
    Convert ML prediction in PRD format to the format expected by existing detection service.

    Args:
        ml_prediction: ML prediction following PRD contract
        scene: Satellite scene that was analyzed
        processing_time_ms: Processing time in milliseconds

    Returns:
        Dictionary in format expected by detection_service.process_ml_prediction()
    """
    # Extract geometry from the first (and only) polygon ring
    # Assuming single polygon for simplicity - in production might handle multi-part
    exterior_ring = ml_prediction["geometry"]["coordinates"][0]

    # Convert to format expected by detection service
    # This creates a single spill region matching the overall detection
    unique_suffix = uuid4().hex[:8].upper()
    geoservice = GeospatialService()

    # If ml_prediction already has structured spill_regions, use them
    input_regions = ml_prediction.get("spill_regions") or []
    processed_regions = []

    if input_regions:
        for i, reg in enumerate(input_regions):
            reg_geom = reg.get("geometry") or ml_prediction["geometry"]
            reg_centroid = reg.get("centroid", {"lat": 0.0, "lon": 0.0})
            reg_bbox = reg.get("bbox", {"min_lat": 0.0, "min_lon": 0.0, "max_lat": 0.0, "max_lon": 0.0})

            # Calculate centroid & bbox from geometry if valid
            try:
                geom_shape = shape(reg_geom)
                if not geom_shape.is_empty and geom_shape.area > 0:
                    c = geoservice.calculate_centroid(from_shape(geom_shape, srid=4326))
                    if c:
                        reg_centroid = {"lat": c["lat"], "lon": c["lon"]}
                    b = geoservice.calculate_bounding_box(from_shape(geom_shape, srid=4326))
                    if b:
                        reg_bbox = b
            except Exception:
                pass

            processed_regions.append({
                "region_id": reg.get("region_id") or f"region_{unique_suffix.lower()}_{i+1}",
                "confidence": float(reg.get("confidence", ml_prediction["confidence"])),
                "area_m2": float(reg.get("area_m2", float(ml_prediction["area_km2"]) * 1_000_000)),
                "centroid": reg_centroid,
                "geometry": reg_geom,
                "bbox": reg_bbox,
                "mask_uri": reg.get("mask_uri"),
                "prediction_uri": reg.get("prediction_uri")
            })
    elif ml_prediction.get("detected"):
        # Create a single default region matching the overall detection ONLY if oil spill was detected
        reg_centroid = {"lat": 0.0, "lon": 0.0}
        reg_bbox = {"min_lat": 0.0, "min_lon": 0.0, "max_lat": 0.0, "max_lon": 0.0}

        try:
            geom_shape = shape(ml_prediction["geometry"])
            if not geom_shape.is_empty and geom_shape.area > 0:
                c = geoservice.calculate_centroid(from_shape(geom_shape, srid=4326))
                if c:
                    reg_centroid = {"lat": c["lat"], "lon": c["lon"]}
                b = geoservice.calculate_bounding_box(from_shape(geom_shape, srid=4326))
                if b:
                    reg_bbox = b
        except Exception:
            pass

        processed_regions = [
            {
                "region_id": f"region_{unique_suffix.lower()}",
                "confidence": float(ml_prediction["confidence"]),
                "area_m2": float(ml_prediction["area_km2"]) * 1_000_000,
                "centroid": reg_centroid,
                "geometry": ml_prediction["geometry"],
                "bbox": reg_bbox,
                "mask_uri": ml_prediction.get("mask_uri"),
                "prediction_uri": ml_prediction.get("prediction_uri")
            }
        ]
    else:
        # Not detected and no regions: leave processed_regions empty
        processed_regions = []

    converted = {
        "analysis_id": f"ANL_{unique_suffix}",
        "scene_id": scene.scene_id,
        "status": "COMPLETED",
        "oil_spill_detected": ml_prediction["detected"],
        "confidence": float(ml_prediction["confidence"]),
        "model_version": ml_prediction["model_version"],
        "processing_time_ms": processing_time_ms,
        "source_scene_id": scene.scene_id,
        "length_km": ml_prediction.get("length_km"),
        "width_km": ml_prediction.get("width_km"),
        "orientation_deg": ml_prediction.get("orientation_deg"),
        "age_estimate_hours": ml_prediction.get("age_estimate_hours"),
        "age_confidence": ml_prediction.get("age_confidence"),
        "spill_regions": processed_regions
    }

    return converted


async def process_ml_inference(
    db: AsyncSession,
    scene: SatelliteScene
) -> SlickDetection:
    """
    Complete ML inference pipeline: invoke model, validate, and persist results.

    Args:
        db: Database session
        scene: Satellite scene to analyze

    Returns:
        SlickDetection: The created detection record

    Raises:
        ValueError: If ML prediction is invalid
        TimeoutError: If ML inference times out
        Exception: For other errors during processing
    """
    start_time = time.time()

    # Get ML provider
    provider = get_ml_provider()

    # Invoke ML inference with timeout
    try:
        ml_prediction = await asyncio.wait_for(
            provider.predict(scene),
            timeout=settings.ML_INFERENCE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        raise TimeoutError(f"ML inference timed out after {settings.ML_INFERENCE_TIMEOUT_SECONDS} seconds")
    except Exception as e:
        raise Exception(f"ML inference failed: {str(e)}")

    # Validate ML prediction
    validate_ml_prediction(ml_prediction)

    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Log inference started
    log_inference(
        service_name="ml_inference_service",
        model_name=ml_prediction.get("model_name", "unknown"),
        model_version=ml_prediction.get("model_version", "unknown"),
        analysis_id="pending",  # Will be updated after conversion
        incident_id="unknown",
        latency_ms=processing_time_ms,
        status_code=200,
        message="ML inference completed successfully"
    )

    # Convert to format expected by existing detection service
    ml_result_for_detection = convert_ml_to_detection_format(
        ml_prediction, scene, processing_time_ms
    )

    # Update analysis_id in log with actual value
    log_inference(
        service_name="ml_inference_service",
        model_name=ml_prediction.get("model_name", "unknown"),
        model_version=ml_prediction.get("model_version", "unknown"),
        analysis_id=ml_result_for_detection["analysis_id"],
        incident_id="unknown",
        latency_ms=processing_time_ms,
        status_code=200,
        message="ML inference completed successfully"
    )

    # Process using existing detection service pipeline
    from app.services.detection_service import process_ml_prediction
    slick = await process_ml_prediction(db, ml_result_for_detection)

    return slick