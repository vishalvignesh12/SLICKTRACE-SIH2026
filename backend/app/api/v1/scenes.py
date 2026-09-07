from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from app.core.database import get_db
from app.core.security import require_analyst
from app.models.satellite_scene import SatelliteScene
from app.schemas.scene import SceneCreate, SceneResponse
from app.services.dashboard_service import to_geojson_polygon
from app.services.satellite_ingestion_service import ingest_satellite_scene

router = APIRouter(prefix="/scenes", tags=["Satellite Scenes"], dependencies=[Depends(require_analyst)])

@router.get("", response_model=List[SceneResponse])
async def list_scenes(db: AsyncSession = Depends(get_db)):
    """List all registered satellite scenes (protected)."""
    stmt = select(SatelliteScene)
    res = await db.execute(stmt)
    scenes = res.scalars().all()
    
    return [
        SceneResponse(
            id=s.id,
            source=s.source,
            scene_id=s.scene_id,
            satellite=s.satellite,
            sensor=s.sensor,
            product_type=s.product_type,
            polarization=s.polarization,
            acquisition_time=s.acquisition_time,
            processing_time=s.processing_time,
            bbox=to_geojson_polygon(s.bbox),
            image_url=s.image_url,
            thumbnail_url=s.thumbnail_url,
            scene_metadata=s.scene_metadata,
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at
        ) for s in scenes
    ]

@router.get("/{id}", response_model=SceneResponse)
async def get_scene(id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve details for a specific satellite scene (protected)."""
    stmt = select(SatelliteScene).where(SatelliteScene.id == id)
    res = await db.execute(stmt)
    s = res.scalars().first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Satellite scene not found")
        
    return SceneResponse(
        id=s.id,
        source=s.source,
        scene_id=s.scene_id,
        satellite=s.satellite,
        sensor=s.sensor,
        product_type=s.product_type,
        polarization=s.polarization,
        acquisition_time=s.acquisition_time,
        processing_time=s.processing_time,
        bbox=to_geojson_polygon(s.bbox),
        image_url=s.image_url,
        thumbnail_url=s.thumbnail_url,
        scene_metadata=s.scene_metadata,
        status=s.status,
        created_at=s.created_at,
        updated_at=s.updated_at
    )

@router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(req: SceneCreate, db: AsyncSession = Depends(get_db)):
    """Register metadata for a new satellite scene (protected)."""
    geom = from_shape(shape(req.bbox.model_dump()), srid=4326)

    s = SatelliteScene(
        source=req.source,
        scene_id=req.scene_id,
        satellite=req.satellite,
        sensor=req.sensor,
        product_type=req.product_type,
        polarization=req.polarization,
        acquisition_time=req.acquisition_time,
        processing_time=req.processing_time,
        bbox=geom,
        image_url=req.image_url,
        thumbnail_url=req.thumbnail_url,
        scene_metadata=req.scene_metadata,
        status=req.status or 'RECEIVED'
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)

    return SceneResponse(
        id=s.id,
        source=s.source,
        scene_id=s.scene_id,
        satellite=s.satellite,
        sensor=s.sensor,
        product_type=s.product_type,
        polarization=s.polarization,
        acquisition_time=s.acquisition_time,
        processing_time=s.processing_time,
        bbox=to_geojson_polygon(s.bbox),
        image_url=s.image_url,
        thumbnail_url=s.thumbnail_url,
        scene_metadata=s.scene_metadata,
        status=s.status,
        created_at=s.created_at,
        updated_at=s.updated_at
    )


@router.post("/ingest", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def ingest_scene(
    req: SceneCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a satellite scene from external source (e.g., replay system).
    Validates metadata, checks for duplicates, persists scene, and creates analysis job.
    This endpoint does NOT wait for AI inference to complete.
    """
    try:
        result = await ingest_satellite_scene(db, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Add background task for any post-processing if needed
    # background_tasks.add_task(some_post_process_function, result)

    return result
