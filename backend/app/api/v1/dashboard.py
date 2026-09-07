from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.core.security import require_analyst
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    DashboardIncidentsResponse,
    DashboardSpillsResponse,
    DashboardVesselsResponse,
    DashboardActivityResponse,
    InvestigationDetailResponse
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_analyst)])


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Get high-level dashboard statistics.

    Returns aggregated counts and measurements for the dashboard overview.
    """
    service = DashboardService(db)
    return await service.get_overview()


@router.get("/incidents", response_model=DashboardIncidentsResponse)
async def get_recent_incidents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by incident status"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent oil-spill incidents with pagination and filtering.

    Returns a paginated list of incidents sorted by detection time (newest first).
    """
    service = DashboardService(db)
    return await service.get_incidents(
        page=page,
        page_size=page_size,
        status=status,
        min_confidence=min_confidence
    )


@router.get("/spills", response_model=DashboardSpillsResponse)
async def get_spill_map(
    status: Optional[str] = Query(None, description="Filter by incident status"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    bbox: Optional[List[float]] = Query(None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detected spill regions as GeoJSON FeatureCollection.

    Returns spill polygons suitable for direct consumption by mapping libraries.
    """
    service = DashboardService(db)
    return await service.get_spills(
        status=status,
        min_confidence=min_confidence,
        bbox=bbox
    )


@router.get("/vessels", response_model=DashboardVesselsResponse)
async def get_vessel_candidates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    incident_id: Optional[UUID] = Query(None, description="Filter by incident ID"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum attribution score"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ranked vessel candidates for attribution.

    Returns vessels ranked by attribution score, preserving the ranking from the attribution layer.
    """
    service = DashboardService(db)
    return await service.get_vessel_candidates(
        page=page,
        page_size=page_size,
        incident_id=incident_id,
        min_score=min_score
    )


@router.get("/activity", response_model=DashboardActivityResponse)
async def get_recent_activity(
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent system activity feed.

    Returns a list of recent system events for the activity feed.
    """
    service = DashboardService(db)
    return await service.get_activity()


@router.get("/investigations/{investigation_id}", response_model=InvestigationDetailResponse)
async def get_investigation_details(
    investigation_id: UUID = Path(..., description="Investigation ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete investigation summary.

    Returns aggregated data for the investigation screen, avoiding the need for multiple domain endpoints.
    Returns 404 if investigation does not exist.
    """
    service = DashboardService(db)
    details = await service.get_investigation_details(investigation_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found"
        )
    return details