from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.exc import IntegrityError
from app.models.investigation import Investigation, InvestigationStatus, InvestigationPriority
from app.models.investigation_event import InvestigationEvent
from app.models.slick_detection import SlickDetection
from app.models.incident import Incident
from app.models.drift_result import DriftResult
from app.models.attribution import AttributionScore
from app.models.vessel import Vessel
from app.models.ais_track import AISTrack
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from app.services.evidence_service import get_evidence
from app.services.ais_service import detect_ais_gaps, query_ais_tracks
from app.schemas.investigation import (
    InvestigationEntityCreate,
    InvestigationEntityUpdate,
    InvestigationEntityResponse,
    InvestigationAggregatedResponse,
    InvestigationEventCreate,
    InvestigationEventResponse
)

async def create_investigation(db: AsyncSession, investigation_in: InvestigationEntityCreate) -> Tuple[Investigation, InvestigationEvent]:
    """
    Create a new investigation and an initial INVESTIGATION_CREATED event atomically.
    """
    # Check if the detection exists
    result = await db.execute(select(SlickDetection).where(SlickDetection.id == investigation_in.detection_id))
    detection = result.scalars().first()
    if not detection:
        raise ValueError(f"Detection with id {investigation_in.detection_id} not found")

    # Create the investigation
    investigation = Investigation(
        detection_id=investigation_in.detection_id,
        title=investigation_in.title,
        description=investigation_in.description,
        priority=investigation_in.priority,
        status=InvestigationStatus.OPEN  # Initial status is OPEN
    )
    db.add(investigation)
    await db.flush()  # To get the investigation ID

    # Create the initial event
    event = InvestigationEvent(
        investigation_id=investigation.id,
        event_type="INVESTIGATION_CREATED",
        message="Investigation created",
        event_metadata=json.dumps({})  # Could include detection info if needed
    )
    db.add(event)

    # Commit will be handled by the caller, but we flush to get IDs
    await db.flush()

    return investigation, event

async def get_investigation(db: AsyncSession, investigation_id: UUID) -> Optional[Investigation]:
    """
    Get an investigation by its ID.
    """
    result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    return result.scalars().first()

async def get_investigations(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    detection_id: Optional[UUID] = None
) -> List[Investigation]:
    """
    Get a list of investigations with optional filters.
    """
    query = select(Investigation)
    conditions = []
    if status:
        conditions.append(Investigation.status == status)
    if priority:
        conditions.append(Investigation.priority == priority)
    if detection_id:
        conditions.append(Investigation.detection_id == detection_id)

    if conditions:
        query = query.where(and_(*conditions))

    if hasattr(skip, "default"):
        skip = skip.default
    if hasattr(limit, "default"):
        limit = limit.default
    skip_val = int(skip) if skip is not None else 0
    limit_val = int(limit) if limit is not None else 100

    query = query.offset(skip_val).limit(limit_val)
    result = await db.execute(query)
    return result.scalars().all()

async def update_investigation(
    db: AsyncSession,
    investigation_id: UUID,
    investigation_in: InvestigationEntityUpdate
) -> Optional[Investigation]:
    """
    Update an investigation's mutable fields.
    """
    investigation = await get_investigation(db, investigation_id)
    if not investigation:
        return None

    update_data = investigation_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(investigation, field, value)

    investigation.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return investigation

async def change_investigation_status(
    db: AsyncSession,
    investigation_id: UUID,
    new_status: InvestigationStatus
) -> Tuple[Optional[Investigation], Optional[InvestigationEvent]]:
    """
    Change the status of an investigation with validation and create a status changed event.
    """
    investigation = await get_investigation(db, investigation_id)
    if not investigation:
        return None, None

    # Define allowed transitions
    allowed_transitions = {
        InvestigationStatus.OPEN: [InvestigationStatus.ANALYZING, InvestigationStatus.DISMISSED],
        InvestigationStatus.ANALYZING: [InvestigationStatus.REVIEW, InvestigationStatus.DISMISSED],
        InvestigationStatus.REVIEW: [InvestigationStatus.RESOLVED, InvestigationStatus.DISMISSED],
        InvestigationStatus.RESOLVED: [],  # Terminal state
        InvestigationStatus.DISMISSED: []   # Terminal state
    }

    if new_status not in allowed_transitions[investigation.status]:
        # Invalid transition
        return investigation, None

    old_status = investigation.status
    investigation.status = new_status
    investigation.updated_at = datetime.now(timezone.utc)

    # If status is RESOLVED or DISMISSED, set closed_at
    if new_status in [InvestigationStatus.RESOLVED, InvestigationStatus.DISMISSED]:
        investigation.closed_at = datetime.now(timezone.utc)

    # Create a status changed event
    event = InvestigationEvent(
        investigation_id=investigation.id,
        event_type="STATUS_CHANGED",
        message=f"Status changed from {old_status.value} to {new_status.value}",
        event_metadata=json.dumps({"from": old_status.value, "to": new_status.value})
    )
    db.add(event)

    await db.flush()
    return investigation, event

async def add_investigation_event(
    db: AsyncSession,
    event_in: InvestigationEventCreate
) -> InvestigationEvent:
    """
    Add a custom event to an investigation.
    """
    meta = event_in.event_metadata if isinstance(event_in.event_metadata, str) else json.dumps(event_in.event_metadata or {})
    event = InvestigationEvent(
        investigation_id=event_in.investigation_id,
        event_type=event_in.event_type,
        message=event_in.message,
        event_metadata=meta
    )
    db.add(event)
    await db.flush()
    return event

# Helper function to convert Investigation model to InvestigationEntityResponse
def investigation_to_response(investigation: Investigation) -> InvestigationEntityResponse:
    return InvestigationEntityResponse.from_orm(investigation)


async def get_investigation_details(db: AsyncSession, incident_id: UUID) -> Optional[InvestigationAggregatedResponse]:
    """
    Get aggregated investigation details for the dashboard (backward compatibility).
    """
    # 1. Fetch Incident
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalars().first()
    if not incident:
        return None

    incident_dict = {
        "id": str(incident.id),
        "name": incident.name,
        "description": incident.description,
        "timestamp": incident.timestamp.isoformat() if incident.timestamp else None,
        "location": None,  # We'll skip the geometry conversion for simplicity, or we can add it
        "status": incident.status,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None
    }

    # 2. Fetch Slick Detection
    result = await db.execute(select(SlickDetection).where(SlickDetection.incident_id == incident_id))
    slick = result.scalars().first()
    slick_dict = None
    if slick:
        # Convert geometry to geojson dict
        geom = None
        if slick.geometry is not None:
            geom = to_shape(slick.geometry)
            geom = mapping(geom)
        slick_dict = {
            "id": str(slick.id),
            "detected": slick.detected,
            "confidence": slick.confidence,
            "model_version": slick.model_version,
            "processing_time_ms": slick.processing_time_ms,
            "source_scene_id": slick.source_scene_id,
            "geometry": geom,
            "area_km2": slick.area_km2,
            "length_km": slick.length_km,
            "width_km": slick.width_km,
            "orientation_deg": slick.orientation_deg,
            "age_estimate_hours": slick.age_estimate_hours,
            "age_confidence": slick.age_confidence,
            "created_at": slick.created_at.isoformat() if slick.created_at else None
        }

    # 3. Fetch Drift Results
    result = await db.execute(select(DriftResult).where(DriftResult.incident_id == incident_id))
    drifts = result.scalars().all()
    drift_dict = None
    if drifts:
        # Take the first drift result (or we could take the one with hindcast or forecast)
        drift = drifts[0]
        # Convert geometries
        origin_point = None
        if drift.origin_point is not None:
            origin_point = to_shape(drift.origin_point)
            origin_point = mapping(origin_point)
        origin_probability_cone = None
        if drift.origin_probability_cone is not None:
            origin_probability_cone = to_shape(drift.origin_probability_cone)
            origin_probability_cone = mapping(origin_probability_cone)
        hindcast_path = None
        if drift.hindcast_path is not None:
            hindcast_path = to_shape(drift.hindcast_path)
            hindcast_path = mapping(hindcast_path)
        forecast_path = None
        if drift.forecast_path is not None:
            forecast_path = to_shape(drift.forecast_path)
            forecast_path = mapping(forecast_path)
        drift_dict = {
            "id": str(drift.id),
            "origin_point": origin_point,
            "origin_probability_cone": origin_probability_cone,
            "origin_time_estimate": drift.origin_time_estimate.isoformat() if drift.origin_time_estimate else None,
            "origin_confidence": drift.origin_confidence,
            "hindcast_path": hindcast_path,
            "forecast_path": forecast_path,
            "created_at": drift.created_at.isoformat() if drift.created_at else None
        }

    # 4. Fetch Attribution Scores & Vessels
    result = await db.execute(
        select(AttributionScore)
        .where(AttributionScore.incident_id == incident_id)
        .order_by(AttributionScore.score.desc())
    )
    scores = result.scalars().all()
    vessels_list = []
    attribution_list = []
    ais_alerts_list = []

    # For AIS tracks, we need to query for vessels in the timeframe
    # We'll get all vessels that have attribution scores
    vessel_ids = [score.vessel_id for score in scores]
    # We'll query AIS tracks for these vessels around the incident time
    # We'll use a time window of ±12 hours around the incident timestamp
    if incident.timestamp:
        start_time = incident.timestamp - timedelta(hours=12)
        end_time = incident.timestamp + timedelta(hours=12)
        all_tracks = await query_ais_tracks(db, start_time, end_time)
    else:
        all_tracks = []

    for score in scores:
        # Get vessel
        result = await db.execute(select(Vessel).where(Vessel.id == score.vessel_id))
        vessel = result.scalars().first()
        if vessel:
            vessel_dict = {
                "id": str(vessel.id),
                "mmsi": vessel.mmsi,
                "imo": vessel.imo,
                "name": vessel.name,
                "type": vessel.type,
                "flag": vessel.flag,
                "length": vessel.length
            }
            vessels_list.append(vessel_dict)

            attribution_dict = {
                "vessel_id": str(score.vessel_id),
                "mmsi": vessel.mmsi if vessel else None,
                "name": vessel.name if vessel else None,
                "score": score.score,
                "proximity": score.proximity_score,
                "temporality": score.temporality_score,
                "trajectory_parity": score.trajectory_score,
                "anomaly_score": score.anomaly_score,
                "anomaly_flag": score.anomaly_flag
            }
            attribution_list.append(attribution_dict)

            # AIS gaps for this vessel
            vessel_tracks = [t for t in all_tracks if t.vessel_id == vessel.id] if vessel else []
            gaps = await detect_ais_gaps(vessel_tracks, threshold_hours=2.0)
            for gap in gaps:
                ais_alerts_list.append({
                    "anomaly_flag": True,
                    "gap_start": gap["gap_start"],
                    "gap_end": gap["gap_end"],
                    "priority": gap["priority"],
                    "explanation": f"{vessel.name if vessel else 'Unknown'}: {gap['explanation']}"
                })

    # 5. Fetch Evidence
    evidence = await get_evidence(db, incident_id)
    evidence_dict = evidence.model_dump() if evidence else None

    # 6. Return the aggregated response
    return InvestigationAggregatedResponse(
        incident=incident_dict,
        slick=slick_dict,
        drift=drift_dict,
        vessels=vessels_list,
        attribution=attribution_list,
        ais_alerts=ais_alerts_list,
        evidence=evidence_dict
    )