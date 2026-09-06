from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from app.core.database import get_db
from app.core.security import require_analyst
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentResponse, GeoJSONPoint
from app.services.dashboard_service import to_geojson_point

router = APIRouter(prefix="/incidents", tags=["Incidents"], dependencies=[Depends(require_analyst)])

@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all incidents with optional filtering by date range and status (protected)."""
    stmt = select(Incident)
    if start_date:
        stmt = stmt.where(Incident.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(Incident.timestamp <= end_date)
    if status:
        stmt = stmt.where(Incident.status == status)
        
    res = await db.execute(stmt)
    incidents = res.scalars().all()
    
    return [
        IncidentResponse(
            id=inc.id,
            name=inc.name,
            description=inc.description,
            timestamp=inc.timestamp,
            location=to_geojson_point(inc.location),
            status=inc.status,
            created_at=inc.created_at,
            updated_at=inc.updated_at
        ) for inc in incidents
    ]

@router.get("/{id}", response_model=IncidentResponse)
async def get_incident(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve details for a specific incident by UUID or string name/code (protected)."""
    inc_uuid = None
    try:
        inc_uuid = UUID(id)
    except ValueError:
        pass

    if inc_uuid:
        stmt = select(Incident).where(Incident.id == inc_uuid)
    else:
        stmt = select(Incident).where(Incident.name == id)

    res = await db.execute(stmt)
    inc = res.scalars().first()

    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        
    return IncidentResponse(
        id=inc.id,
        name=inc.name,
        description=inc.description,
        timestamp=inc.timestamp,
        location=to_geojson_point(inc.location),
        status=inc.status,
        created_at=inc.created_at,
        updated_at=inc.updated_at
    )

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(req: IncidentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new incident (protected)."""
    # Convert GeoJSON point to Shapely shape then to GeoAlchemy2 element
    geom = from_shape(shape(req.location.model_dump()), srid=4326)
    
    inc = Incident(
        name=req.name,
        description=req.description,
        timestamp=req.timestamp,
        location=geom,
        status=req.status
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    
    return IncidentResponse(
        id=inc.id,
        name=inc.name,
        description=inc.description,
        timestamp=inc.timestamp,
        location=to_geojson_point(inc.location),
        status=inc.status,
        created_at=inc.created_at,
        updated_at=inc.updated_at
    )

@router.put("/{id}", response_model=IncidentResponse)
async def update_incident(id: str, req: IncidentCreate, db: AsyncSession = Depends(get_db)):
    """Update details for an existing incident (protected)."""
    inc_uuid = None
    try:
        inc_uuid = UUID(id)
    except ValueError:
        pass

    if inc_uuid:
        stmt = select(Incident).where(Incident.id == inc_uuid)
    else:
        stmt = select(Incident).where(Incident.name == id)

    res = await db.execute(stmt)
    inc = res.scalars().first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        
    geom = from_shape(shape(req.location.model_dump()), srid=4326)
    
    inc.name = req.name
    inc.description = req.description
    inc.timestamp = req.timestamp
    inc.location = geom
    inc.status = req.status
    
    await db.commit()
    await db.refresh(inc)
    
    return IncidentResponse(
        id=inc.id,
        name=inc.name,
        description=inc.description,
        timestamp=inc.timestamp,
        location=to_geojson_point(inc.location),
        status=inc.status,
        created_at=inc.created_at,
        updated_at=inc.updated_at
    )
