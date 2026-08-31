from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_analyst
from app.models.investigation import InvestigationStatus
from app.models.investigation_event import InvestigationEvent
from app.models.investigation import InvestigationStatus
from app.services.investigation_service import (
    create_investigation,
    get_investigation,
    get_investigations,
    update_investigation,
    change_investigation_status,
    add_investigation_event,
    investigation_to_response,
    get_investigation_details
)
from app.schemas.investigation import (
    InvestigationEntityCreate,
    InvestigationEntityUpdate,
    InvestigationEntityResponse,
    InvestigationEventCreate,
    InvestigationEventResponse,
    InvestigationEventBase,
    InvestigationAggregatedResponse
)

router = APIRouter(prefix="/investigations", tags=["Investigations"], dependencies=[Depends(require_analyst)])

@router.post("/", response_model=InvestigationEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation_endpoint(
    investigation_in: InvestigationEntityCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new investigation.
    """
    try:
        investigation, event = await create_investigation(db, investigation_in)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    return investigation_to_response(investigation)

@router.get("/{investigation_id}", response_model=InvestigationEntityResponse)
async def get_investigation_endpoint(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get an investigation by ID.
    """
    investigation = await get_investigation(db, investigation_id)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return investigation_to_response(investigation)

@router.get("/", response_model=List[InvestigationEntityResponse])
async def list_investigations_endpoint(
    skip: int = 0,
    limit: int = Query(100, lte=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    detection_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List investigations with optional filtering and pagination.
    """
    investigations = await get_investigations(
        db, skip=skip, limit=limit, status=status, priority=priority, detection_id=detection_id
    )
    return [investigation_to_response(inv) for inv in investigations]

@router.patch("/{investigation_id}", response_model=InvestigationEntityResponse)
async def update_investigation_endpoint(
    investigation_id: UUID,
    investigation_in: InvestigationEntityUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an investigation.
    """
    investigation = await update_investigation(db, investigation_id, investigation_in)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    return investigation_to_response(investigation)

@router.patch("/{investigation_id}/status", response_model=InvestigationEntityResponse)
async def change_investigation_status_endpoint(
    investigation_id: UUID,
    new_status: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Change the status of an investigation.
    """
    try:
        status_enum = InvestigationStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {new_status}")

    investigation, event = await change_investigation_status(db, investigation_id, status_enum)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    if event is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status transition from {investigation.status} to {new_status}")

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    return investigation_to_response(investigation)

@router.get("/{investigation_id}/timeline", response_model=List[InvestigationEventResponse])
async def get_investigation_timeline_endpoint(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the timeline of events for an investigation.
    """
    # First check if investigation exists
    investigation = await get_investigation(db, investigation_id)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    # Get events ordered by created_at descending
    result = await db.execute(
        select(InvestigationEvent)
        .where(InvestigationEvent.investigation_id == investigation_id)
        .order_by(InvestigationEvent.created_at.desc())
    )
    events = result.scalars().all()
    return [InvestigationEventResponse.from_orm(event) for event in events]


@router.get("/by-incident/{incident_id}", response_model=InvestigationAggregatedResponse)
async def get_investigation_by_incident_endpoint(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated investigation details by incident ID (for dashboard backward compatibility).
    """
    result = await get_investigation_details(db, incident_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found for incident")
    return result


@router.get("/{investigation_id}/evidence", response_model=dict)
async def get_investigation_evidence_endpoint(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get evidence details for an investigation.
    """
    # First check if investigation exists
    investigation = await get_investigation(db, investigation_id)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    # Get evidence using the incident_id from the investigation
    from app.services.evidence_service import get_evidence
    evidence = await get_evidence(db, investigation.incident_id)
    return evidence.model_dump()


@router.get("/{investigation_id}/export")
async def export_investigation_endpoint(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Export investigation data as CSV.
    """
    # First check if investigation exists
    investigation = await get_investigation(db, investigation_id)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    # Generate CSV export
    from app.services.evidence_service import generate_csv_export
    csv_string = await generate_csv_export(db, investigation.incident_id)

    # Return as CSV file download
    from fastapi.responses import Response
    return Response(
        content=csv_string,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=investigation_{investigation_id}.csv"
        }
    )