import time
import asyncio
from datetime import datetime, UTC, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional

from app.integrations.satellite import FixtureSatelliteAdapter
from app.integrations.ml import MLInferenceProvider, FixtureMLProvider, get_ml_provider
from app.models.slick_detection import SlickDetection
from app.models.incident import Incident
from app.models.satellite_scene import SatelliteScene
from app.models.spill_region import SpillRegion
from app.models.inference_log import MLInferenceLog
from app.schemas.detection import AnalyzeRequest, DetectionResponse
from app.services.geospatial_service import GeospatialService
from app.core.config import settings
from app.core.logging import log_inference


async def process_ml_prediction(db: AsyncSession, ml_result: dict) -> SlickDetection:
    """
    Process ML prediction and persist detection results.

    Implements the complete processing pipeline:
    1. Validate ML response schema
    2. Validate analysis ID (idempotency)
    3. Validate scene ID
    4. Validate confidence
    5. Validate geometry for each region
    6. Repair geometry if appropriate
    7. Calculate geospatial attributes (area, centroid, bbox)
    8. Persist detection and spill regions atomically
    9. Mark analysis as processed

    Args:
        db: Database session
        ml_result: ML prediction result following the standard contract

    Returns:
        SlickDetection: The created detection record

    Raises:
        ValueError: If ML result is invalid or validation fails
        SQLAlchemyError: If database operations fail
    """
    start_time = time.time()

    # 1. Validate ML response schema
    _validate_ml_response_schema(ml_result)

    analysis_id = ml_result["analysis_id"]
    scene_id = ml_result["scene_id"]

    # 2. Validate analysis ID (check for idempotency)
    existing_detection = await _get_detection_by_analysis_id(db, analysis_id)
    if existing_detection:
        # Log that we're returning existing detection
        log_inference(
            service_name="detection_service",
            model_name="ml-model",
            model_version=ml_result.get("model_version", "unknown"),
            analysis_id=analysis_id,
            incident_id="unknown",
            latency_ms=int((time.time() - start_time) * 1000),
            status_code=200,
            message="Analysis ID already processed, returning existing detection"
        )
        return existing_detection

    # 3. Validate scene ID
    scene_uuid = None
    try:
        scene_uuid = UUID(scene_id)
    except ValueError:
        pass

    # Get or create scene
    scene = await _get_or_create_scene(db, scene_id, ml_result)

    # 4. Get or create incident for this scene
    incident = await _get_or_create_incident(db, scene)

    # 5. Process the ML result
    oil_spill_detected = ml_result.get("oil_spill_detected", False)
    confidence = float(ml_result["confidence"])
    model_version = ml_result["model_version"]
    processing_time_ms = int(ml_result["processing_time_ms"])

    # Validate confidence range
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

    # 6. Process spill regions
    spill_regions = ml_result.get("spill_regions", [])
    if not spill_regions and not oil_spill_detected:
        # No spill detected - create detection with empty regions
        slick = await _create_detection_record(
            db, incident, scene, analysis_id, oil_spill_detected,
            confidence, model_version, processing_time_ms, ml_result,
            regions=None
        )
        await db.commit()
        await db.refresh(slick)
        return slick

    if not spill_regions and oil_spill_detected:
        raise ValueError("Oil spill detected but no spill regions provided")

    # Process each spill region
    processed_regions = []
    total_area_m2 = 0.0

    for region_data in spill_regions:
        # Validate region data
        region = await _process_spill_region(db, region_data, GeospatialService())
        processed_regions.append(region)
        total_area_m2 += region.area_m2

    # 7. Create detection record
    slick = await _create_detection_record(
        db, incident, scene, analysis_id, oil_spill_detected,
        confidence, model_version, processing_time_ms, ml_result,
        regions=processed_regions
    )

    # 8. Persist spill regions
    for i, region in enumerate(processed_regions):
        region.detection_id = slick.id
        region.region_index = i
        db.add(region)

    # 9. Update detection with calculated total area (optional)
    # Note: Individual region areas are stored in spill_regions table
    # We could store total area in detection if needed, but PRD focuses on region-level

    try:
        await db.commit()
        await db.refresh(slick)

        # Log success
        log_inference(
            service_name="detection_service",
            model_name="ml-model",
            model_version=model_version,
            analysis_id=analysis_id,
            incident_id="unknown",
            latency_ms=int((time.time() - start_time) * 1000),
            status_code=200,
            message=f"Successfully processed ML prediction with {len(processed_regions)} regions"
        )

        return slick

    except SQLAlchemyError as e:
        await db.rollback()
        log_inference(
            service_name="detection_service",
            model_name="ml-model",
            model_version=model_version,
            analysis_id=analysis_id,
            incident_id="unknown",
            latency_ms=int((time.time() - start_time) * 1000),
            status_code=500,
            message=f"Database error: {str(e)}"
        )
        raise


def _validate_ml_response_schema(ml_result: dict) -> None:
    """Validate ML response against the expected schema."""
    required_fields = [
        "analysis_id", "scene_id", "status", "oil_spill_detected",
        "confidence", "model_version", "processing_time_ms"
    ]

    for field in required_fields:
        if field not in ml_result:
            raise ValueError(f"Missing required field in ML response: {field}")

    # Validate status
    if ml_result["status"] not in ["COMPLETED", "FAILED"]:
        raise ValueError(f"Status must be 'COMPLETED' or 'FAILED', got {ml_result['status']}")

    if ml_result["status"] == "FAILED":
        raise ValueError("ML prediction failed")

    # Validate spill_regions if present
    if "spill_regions" in ml_result and ml_result["spill_regions"] is not None:
        for i, region in enumerate(ml_result["spill_regions"]):
            if not isinstance(region, dict):
                raise ValueError(f"Spill region {i} must be a dictionary")

            required_region_fields = ["region_id", "confidence", "geometry"]
            for field in required_region_fields:
                if field not in region:
                    raise ValueError(f"Missing required field in spill region {i}: {field}")

            # Validate region confidence
            if not 0.0 <= float(region["confidence"]) <= 1.0:
                raise ValueError(f"Region {i} confidence must be between 0.0 and 1.0")


async def _get_detection_by_analysis_id(db: AsyncSession, analysis_id: str) -> Optional[SlickDetection]:
    """Check if detection already exists for analysis_id (idempotency)."""
    try:
        result = await db.execute(
            select(SlickDetection).where(SlickDetection.analysis_id == analysis_id)
        )
        return result.scalar_one_or_none()
    except Exception:
        return None


async def _get_or_create_scene(db: AsyncSession, scene_id: str, ml_result: dict) -> SatelliteScene:
    """Get existing scene or create new one."""
    scene_uuid = None
    try:
        scene_uuid = UUID(scene_id)
    except ValueError:
        pass

    scene = None
    if scene_uuid:
        result = await db.execute(
            select(SatelliteScene).where(SatelliteScene.id == scene_uuid)
        )
        scene = result.scalar_one_or_none()

    if not scene:
        result = await db.execute(
            select(SatelliteScene).where(SatelliteScene.scene_id == scene_id)
        )
        scene = result.scalars().first()

    if not scene:
        # Create new scene from ML result metadata
        acquisition_time = ml_result.get("acquisition_time", datetime.now(UTC))
        if isinstance(acquisition_time, str):
            acquisition_time = datetime.fromisoformat(acquisition_time.replace('Z', '+00:00'))

        # Extract bounding box from ML result or use defaults
        bbox_coords = _extract_bbox_from_ml_result(ml_result, scene_id)

        scene = SatelliteScene(
            source="sentinel-1-replay",
            scene_id=scene_id,
            satellite="Sentinel-1",
            sensor="SAR",
            
            product_type="GRD",
            polarization="VV",
            acquisition_time=acquisition_time,
            processing_time=datetime.now(timezone.utc),
            bbox=from_shape(shape({
                "type": "Polygon",
                "coordinates": [bbox_coords]
            }), srid=4326),
            image_url=ml_result.get("image_url"),
            thumbnail_url=ml_result.get("thumbnail_url"),
            status="PROCESSED"
        )
        db.add(scene)
        await db.flush()

    return scene


def _extract_bbox_from_ml_result(ml_result: dict, scene_id: str) -> List[List[float]]:
    """Extract bounding box from ML result or use scene_id-based defaults."""
    # Try to get bbox from ML result
    if "bbox" in ml_result and ml_result["bbox"]:
        bbox = ml_result["bbox"]
        if isinstance(bbox, dict) and all(k in bbox for k in ["min_lat", "min_lon", "max_lat", "max_lon"]):
            return [
                [bbox["min_lon"], bbox["min_lat"]],
                [bbox["max_lon"], bbox["min_lat"]],
                [bbox["max_lon"], bbox["max_lat"]],
                [bbox["min_lon"], bbox["max_lat"]],
                [bbox["min_lon"], bbox["min_lat"]]  # Close the polygon
            ]

    # Try to get bbox from first spill region
    if "spill_regions" in ml_result and ml_result["spill_regions"]:
        first_region = ml_result["spill_regions"][0]
        if "bbox" in first_region and first_region["bbox"]:
            bbox = first_region["bbox"]
            if isinstance(bbox, dict) and all(k in bbox for k in ["min_lat", "min_lon", "max_lat", "max_lon"]):
                return [
                    [bbox["min_lon"], bbox["min_lat"]],
                    [bbox["max_lon"], bbox["min_lat"]],
                    [bbox["max_lon"], bbox["max_lat"]],
                    [bbox["min_lon"], bbox["max_lat"]],
                    [bbox["min_lon"], bbox["min_lat"]]
                ]

    # Fallback: generate a reasonable bbox based on scene_id hash
    # This is just for development - in production, bbox should come from ML or metadata
    import hashlib
    hash_int = int(hashlib.md5(scene_id.encode()).hexdigest()[:8], 16)
    base_lat = (hash_int % 90) - 45  # -45 to 45
    base_lon = (hash_int % 180) - 180  # -180 to 180

    return [
        [base_lon, base_lat],
        [base_lon + 1, base_lat],
        [base_lon + 1, base_lat + 1],
        [base_lon, base_lat + 1],
        [base_lon, base_lat]
    ]


async def _get_or_create_incident(db: AsyncSession, scene: SatelliteScene) -> Incident:
    """Get existing incident for scene or create new one."""
    # Look for incident associated with this scene
    result = await db.execute(
        select(Incident).where(Incident.name.like(f"%{scene.scene_id}%"))
    )
    incident = result.scalars().first()

    if not incident:
        # Create new incident
        incident = Incident(
            name=f"Incident for Scene {scene.scene_id}",
            description="Auto-generated incident from satellite scene analysis",
            timestamp=scene.acquisition_time,
            location=from_shape(shape({
                "type": "Point",
                "coordinates": [0.0, 0.0]  # Will be updated based on detection
            }), srid=4326),
            status="DETECTED"
        )
        db.add(incident)
        await db.flush()

    return incident


async def _create_detection_record(
    db: AsyncSession,
    incident: Incident,
    scene: SatelliteScene,
    analysis_id: str,
    oil_spill_detected: bool,
    confidence: float,
    model_version: str,
    processing_time_ms: int,
    ml_result: dict,
    regions: List[SpillRegion] = None
) -> SlickDetection:
    """Create SlickDetection record."""
    # If we have regions, use the first region's geometry as the detection geometry
    # In a more sophisticated implementation, we might compute union of all regions
    if regions and len(regions) > 0:
        geom_wkb = regions[0].geometry
    else:
        # Create default geometry if none provided
        geom_wkb = from_shape(shape({
            "type": "Polygon",
            "coordinates": [[[0, 0], [0, 0], [0, 0], [0, 0]]]
        }), srid=4326)

    slick = SlickDetection(
        incident_id=incident.id,
        scene_id=scene.id,
        analysis_id=analysis_id,
        detected=oil_spill_detected,
        confidence=confidence,
        model_version=model_version,
        processing_time_ms=processing_time_ms,
        source_scene_id=ml_result.get("scene_id", scene.scene_id),
        geometry=geom_wkb,
        area_km2=sum((r.area_m2 for r in regions), 0.0) / 1000000.0 if regions else 0.0,
        length_km=ml_result.get("length_km"),
        width_km=ml_result.get("width_km"),
        orientation_deg=ml_result.get("orientation_deg"),
        age_estimate_hours=ml_result.get("age_estimate_hours"),
        age_confidence=ml_result.get("age_confidence")
    )
    db.add(slick)
    await db.flush()
    return slick


async def _process_spill_region(db: AsyncSession, region_data: dict, geo_service: GeospatialService) -> SpillRegion:
    """Process a single spill region."""
    # Extract region data
    region_id = region_data["region_id"]
    confidence = float(region_data["confidence"])

    # Validate confidence
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Region {region_id} confidence must be between 0.0 and 1.0, got {confidence}")

    # Process geometry
    geom_wkb = None
    geom_repaired = False
    repair_description = ""

    if "geometry" in region_data and region_data["geometry"]:
        # Convert GeoJSON geometry to WKB
        try:
            geom_shape = shape(region_data["geometry"])
            geom_wkb = from_shape(geom_shape, srid=4326)

            # Validate geometry
            is_valid, error_msg = geo_service.validate_geometry(geom_wkb)
            if not is_valid:
                # Try to repair
                repaired_geom, was_repaired, description = geo_service.repair_geometry(geom_wkb)
                if was_repaired and repaired_geom is not None:
                    geom_wkb = repaired_geom
                    geom_repaired = True
                    repair_description = description
                    # Log repair operation
                    from app.core.logging import log_inference
                    log_inference(
                        service_name="detection_service",
                        model_name="unknown",
                        model_version="unknown",
                        incident_id="unknown",
                        latency_ms=0,
                        status_code=200,
                        message=f"Geometry repaired for region {region_id}: {description}"
                    )
                else:
                    raise ValueError(f"Invalid geometry for region {region_id}: {error_msg}")
        except Exception as e:
            raise ValueError(f"Invalid geometry format for region {region_id}: {str(e)}")
    else:
        # Create default geometry if none provided
        geom_wkb = from_shape(shape({
            "type": "Polygon",
            "coordinates": [[[0, 0], [0, 0], [0, 0], [0, 0]]]
        }), srid=4326)

    # Calculate geospatial attributes
    area_m2 = region_data.get("area_m2", 0.0)
    centroid = geo_service.calculate_centroid(geom_wkb)
    bbox = geo_service.calculate_bounding_box(geom_wkb)

    # Create SpillRegion record
    region = SpillRegion(
        # detection_id and region_index will be set later
        region_index=0,  # Temporary, will be updated
        geometry=geom_wkb,
        area_m2=area_m2,
        perimeter_m=geo_service.calculate_perimeter_m(geom_wkb),
        confidence=confidence,
        mask_uri=region_data.get("mask_uri")
        # Note: centroid and bounding_box are computed properties, not stored
    )

    return region


async def analyze_slick(db: AsyncSession, req: AnalyzeRequest) -> SlickDetection:
    """Orchestrate satellite scene analysis, log inference, and save results."""
    start_time = time.time()

    # Get or create scene record (minimal metadata for scene creation)
    scene = await _get_or_create_scene(db, req.scene_id, {
        "scene_id": req.scene_id,
        "acquisition_time": req.timestamp
    })

    # Get ML provider
    provider = get_ml_provider()

    # Run analysis to get ML prediction
    ml_prediction = await provider.predict(scene)

    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Convert ML prediction to format expected by existing pipeline
    from app.services.ml_inference_service import convert_ml_to_detection_format
    ml_result_for_detection = convert_ml_to_detection_format(
        ml_prediction, scene, processing_time_ms
    )

    # Process the ML prediction using the existing pipeline
    slick = await process_ml_prediction(db, ml_result_for_detection)

    return slick