from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import require_analyst
from app.models.slick_detection import SlickDetection
from app.models.spill_region import SpillRegion
from app.schemas.detection import AnalyzeRequest, DetectionResponse
from app.schemas.region import SpillRegionResponse
from app.services.detection_service import analyze_slick
from app.services.dashboard_service import to_geojson_polygon
from app.services.geospatial_service import GeospatialService

router = APIRouter(prefix="/detections", tags=["Slick Detection"], dependencies=[Depends(require_analyst)])

@router.get("", response_model=List[DetectionResponse])
async def list_detections(db: AsyncSession = Depends(get_db)):
    """List all slick detections (protected)."""
    stmt = select(SlickDetection)
    res = await db.execute(stmt)
    detections = res.scalars().all()

    return [
        DetectionResponse(
            detection_id=d.id,
            slick_polygon=to_geojson_polygon(d.geometry),
            area_km2=d.area_km2,
            length_km=d.length_km,
            width_km=d.width_km,
            orientation_deg=d.orientation_deg,
            confidence=d.confidence,
            age_estimate_hours=d.age_estimate_hours,
            age_confidence=d.age_confidence
        ) for d in detections
    ]

@router.post("/analyze", response_model=DetectionResponse, status_code=status.HTTP_201_CREATED)
async def analyze(req: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """Analyze a satellite scene to detect and characterize oil slicks (protected)."""
    slick = await analyze_slick(db, req)
    return DetectionResponse(
        detection_id=slick.id,
        slick_polygon=to_geojson_polygon(slick.geometry),
        area_km2=slick.area_km2,
        length_km=slick.length_km,
        width_km=slick.width_km,
        orientation_deg=slick.orientation_deg,
        confidence=slick.confidence,
        age_estimate_hours=slick.age_estimate_hours,
        age_confidence=slick.age_confidence
    )


@router.get("/analysis/{analysis_id}", response_model=DetectionResponse)
async def get_detection_by_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Get detection by analysis ID."""
    stmt = select(SlickDetection).where(SlickDetection.analysis_id == analysis_id)
    res = await db.execute(stmt)
    detection = res.scalars().first()

    if not detection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found for analysis ID")

    return DetectionResponse(
        detection_id=detection.id,
        slick_polygon=to_geojson_polygon(detection.geometry),
        area_km2=detection.area_km2,
        length_km=detection.length_km,
        width_km=detection.width_km,
        orientation_deg=detection.orientation_deg,
        confidence=detection.confidence,
        age_estimate_hours=detection.age_estimate_hours,
        age_confidence=detection.age_confidence
    )


@router.get("/scene/{scene_id}", response_model=List[DetectionResponse])
async def get_detections_by_scene(scene_id: str, db: AsyncSession = Depends(get_db)):
    """Get all detections for a scene."""
    # First get the scene to get its ID
    from app.models.satellite_scene import SatelliteScene
    stmt_scene = select(SatelliteScene).where(SatelliteScene.scene_id == scene_id)
    res_scene = await db.execute(stmt_scene)
    scene = res_scene.scalars().first()

    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    # Get detections for this scene
    stmt = select(SlickDetection).where(SlickDetection.scene_id == scene.id)
    res = await db.execute(stmt)
    detections = res.scalars().all()

    return [
        DetectionResponse(
            detection_id=d.id,
            slick_polygon=to_geojson_polygon(d.geometry),
            area_km2=d.area_km2,
            length_km=d.length_km,
            width_km=d.width_km,
            orientation_deg=d.orientation_deg,
            confidence=d.confidence,
            age_estimate_hours=d.age_estimate_hours,
            age_confidence=d.age_confidence
        ) for d in detections
    ]


@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(detection_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific detection by ID."""
    stmt = select(SlickDetection).where(SlickDetection.id == detection_id)
    res = await db.execute(stmt)
    detection = res.scalars().first()

    if not detection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")

    return DetectionResponse(
        detection_id=detection.id,
        slick_polygon=to_geojson_polygon(detection.geometry),
        area_km2=detection.area_km2,
        length_km=detection.length_km,
        width_km=detection.width_km,
        orientation_deg=detection.orientation_deg,
        confidence=detection.confidence,
        age_estimate_hours=detection.age_estimate_hours,
        age_confidence=detection.age_confidence
    )


@router.get("/{detection_id}/regions/{region_id}", response_model=SpillRegionResponse)
async def get_spill_region(detection_id: UUID, region_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific spill region by detection ID and region ID."""
    # Verify the detection exists and belongs to this region
    stmt = select(SpillRegion).where(
        SpillRegion.id == region_id,
        SpillRegion.detection_id == detection_id
    )
    res = await db.execute(stmt)
    region = res.scalars().first()

    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spill region not found for this detection"
        )

    # Calculate centroid and bounding box from geometry
    geoservice = GeospatialService()
    centroid = geoservice.calculate_centroid(region.geometry)
    bbox = geoservice.calculate_bounding_box(region.geometry)

    if centroid is None or bbox is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not calculate centroid or bounding box for region"
        )

    # Convert geometry to GeoJSON
    geometry_geojson = geoservice.convert_to_geojson(region.geometry)
    if geometry_geojson is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not convert geometry to GeoJSON"
        )

    return SpillRegionResponse(
        id=region.id,
        confidence=region.confidence,
        area_m2=region.area_m2,
        perimeter_m=region.perimeter_m,
        centroid={"lat": centroid["lat"], "lon": centroid["lon"]},
        bbox={
            "min_lat": bbox["min_lat"],
            "min_lon": bbox["min_lon"],
            "max_lat": bbox["max_lat"],
            "max_lon": bbox["max_lon"]
        },
        geometry=geometry_geojson,
        mask_uri=region.mask_uri,
        created_at=region.created_at
    )
