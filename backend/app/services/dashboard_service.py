from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, literal
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from datetime import datetime, timezone, timedelta

from app.models.incident import Incident
from app.models.slick_detection import SlickDetection
from app.models.attribution import AttributionScore
from app.models.vessel import Vessel
from app.models.drift_result import DriftResult
from app.models.ais_track import AISTrack
from app.models.spill_region import SpillRegion
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    IncidentItemResponse,
    DashboardIncidentsResponse,
    DashboardSpillsResponse,
    VesselCandidateItemResponse,
    DashboardVesselsResponse,
    ActivityEventResponse,
    DashboardActivityResponse,
    InvestigationDetailResponse
)
from app.schemas.incident import GeoJSONPoint
from app.schemas.scene import GeoJSONPolygon


def to_geojson_point(geom) -> Optional[dict]:
    """Convert SQLAlchemy geometry to GeoJSON point."""
    if geom is None:
        return None
    shape_obj = to_shape(geom)
    return {
        "type": "Point",
        "coordinates": [shape_obj.x, shape_obj.y]
    }


def to_geojson_polygon(geom) -> Optional[dict]:
    """Convert SQLAlchemy geometry to GeoJSON polygon."""
    if geom is None:
        return None
    shape_obj = to_shape(geom)
    coords = mapping(shape_obj)["coordinates"]
    return {
        "type": "Polygon",
        "coordinates": [list(ring) for ring in coords]
    }


def to_geojson_linestring(geom) -> Optional[dict]:
    """Convert SQLAlchemy geometry to GeoJSON linestring."""
    if geom is None:
        return None
    shape_obj = to_shape(geom)
    return {
        "type": "LineString",
        "coordinates": list(mapping(shape_obj)["coordinates"])
    }

class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self) -> DashboardOverviewResponse:
        """Get dashboard overview statistics."""
        # Total incidents
        total_incidents_stmt = select(func.count(Incident.id))
        total_incidents_result = await self.db.execute(total_incidents_stmt)
        total_incidents = total_incidents_result.scalar() or 0

        # Active incidents (those with status not VERIFIED or similar)
        active_incidents_stmt = select(func.count(Incident.id)).where(
            Incident.status.in_(["DETECTED", "INVESTIGATING", "INVESTIGATION_READY"])
        )
        active_incidents_result = await self.db.execute(active_incidents_stmt)
        active_incidents = active_incidents_result.scalar() or 0

        # Detected spills (detections where oil was detected)
        detected_spills_stmt = select(func.count(SlickDetection.id)).where(
            SlickDetection.detected == True
        )
        detected_spills_result = await self.db.execute(detected_spills_stmt)
        detected_spills = detected_spills_result.scalar() or 0

        # Total spill area (sum of area_km2 from detections)
        total_spill_area_stmt = select(func.coalesce(func.sum(SlickDetection.area_km2), 0)).where(
            SlickDetection.detected == True
        )
        total_spill_area_result = await self.db.execute(total_spill_area_stmt)
        total_spill_area_km2 = float(total_spill_area_result.scalar() or 0)

        # Analyses completed (this would come from some analysis table, using detections as proxy for now)
        analyses_completed_stmt = select(func.count(SlickDetection.id)).where(
            and_(SlickDetection.detected == True, SlickDetection.confidence >= 0.8)
        )
        analyses_completed_result = await self.db.execute(analyses_completed_stmt)
        analyses_completed = analyses_completed_result.scalar() or 0

        # Analyses processing (detections with low confidence or pending)
        analyses_processing_stmt = select(func.count(SlickDetection.id)).where(
            and_(SlickDetection.detected == True, SlickDetection.confidence < 0.8)
        )
        analyses_processing_result = await self.db.execute(analyses_processing_stmt)
        analyses_processing = analyses_processing_result.scalar() or 0

        # Analyses failed (this would be from a failed analyses table, using 0 for now)
        analyses_failed = 0

        # High confidence spills (detections with confidence >= 0.8)
        high_confidence_spills_stmt = select(func.count(SlickDetection.id)).where(
            and_(SlickDetection.detected == True, SlickDetection.confidence >= 0.8)
        )
        high_confidence_spills_result = await self.db.execute(high_confidence_spills_stmt)
        high_confidence_spills = high_confidence_spills_result.scalar() or 0

        return DashboardOverviewResponse(
            total_incidents=total_incidents,
            active_incidents=active_incidents,
            detected_spills=detected_spills,
            total_spill_area_km2=total_spill_area_km2,
            analyses_completed=analyses_completed,
            analyses_processing=analyses_processing,
            analyses_failed=analyses_failed,
            high_confidence_spills=high_confidence_spills
        )

    async def get_incidents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> DashboardIncidentsResponse:
        """Get recent incidents with pagination and filtering."""
        # Build base query
        query = select(
            Incident.id,
            Incident.status,
            Incident.timestamp,
            SlickDetection.confidence,
            SlickDetection.area_km2,
            Incident.location
        ).select_from(
            Incident.__table__.join(SlickDetection.__table__, Incident.id == SlickDetection.incident_id, isouter=True)
        )

        # Apply filters
        filters = []
        if status:
            filters.append(Incident.status == status)
        if min_confidence is not None:
            filters.append(SlickDetection.confidence >= min_confidence)

        if filters:
            query = query.where(and_(*filters))

        # Order by detected_at descending (most recent first)
        query = query.order_by(Incident.timestamp.desc())

        # Get total count
        count_query = select(func.count()).select_from(
            Incident.__table__.join(SlickDetection.__table__, Incident.id == SlickDetection.incident_id, isouter=True)
        )
        if filters:
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Build response items
        items = []
        for row in rows:
            incident_id, status, timestamp, confidence, area_km2, location = row
            items.append(IncidentItemResponse(
                incident_id=incident_id,
                status=status or "UNKNOWN",
                detected_at=timestamp.isoformat() if timestamp else "",
                confidence=float(confidence) if confidence is not None else 0.0,
                area_km2=float(area_km2) if area_km2 is not None else 0.0,
                location=to_geojson_point(location) or {"type": "Point", "coordinates": [0, 0]}
            ))

        return DashboardIncidentsResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total
        )

    async def get_spills(
        self,
        status: Optional[str] = None,
        min_confidence: Optional[float] = None,
        bbox: Optional[List[float]] = None
    ) -> DashboardSpillsResponse:
        """Get spill regions as GeoJSON FeatureCollection."""
        # Build query for spill regions with their associated detections and incidents
        query = select(
            SpillRegion.id,
            SpillRegion.detection_id,
            SpillRegion.region_index,
            SpillRegion.geometry,
            SpillRegion.area_m2,
            SpillRegion.confidence,
            SlickDetection.incident_id,
            SlickDetection.id.label('detection_id_alias'),
            Incident.id.label('incident_id_alias')
        ).select_from(
            SpillRegion.__table__
            .join(SlickDetection.__table__, SpillRegion.detection_id == SlickDetection.id)
            .join(Incident.__table__, SlickDetection.incident_id == Incident.id)
        )

        # Apply filters
        filters = [SlickDetection.detected == True]  # Only show detected spills
        if status and isinstance(status, str):
            filters.append(Incident.status == status)
        if min_confidence is not None and isinstance(min_confidence, (int, float)):
            filters.append(SlickDetection.confidence >= min_confidence)
        if bbox is not None and isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            # bbox format: [minx, miny, maxx, maxy] = [lon_min, lat_min, lon_max, lat_max]
            # PostGIS ST_MakeEnvelope(xmin, ymin, xmax, ymax, srid)
            bbox_geom = func.ST_MakeEnvelope(bbox[0], bbox[1], bbox[2], bbox[3], 4326)
            filters.append(func.ST_Intersects(SpillRegion.geometry, bbox_geom))

        if filters:
            query = query.where(and_(*filters))

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Build GeoJSON FeatureCollection
        features = []
        for row in rows:
            region_id, detection_id, region_index, geometry, area_m2, confidence, incident_id, detection_id_alias, incident_id_alias = row

            # Convert area from m2 to km2
            area_km2 = area_m2 / 1000000.0 if area_m2 else 0.0

            feature = {
                "type": "Feature",
                "geometry": to_geojson_polygon(geometry) or {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]]
                },
                "properties": {
                    "incident_id": str(incident_id),
                    "detection_id": str(detection_id),
                    "confidence": float(confidence) if confidence else 0.0,
                    "area_km2": area_km2,
                    "status": "ACTIVE"  # Could derive from incident status
                }
            }
            features.append(feature)

        return DashboardSpillsResponse(
            type="FeatureCollection",
            features=features
        )

    async def get_vessel_candidates(
        self,
        page: int = 1,
        page_size: int = 20,
        incident_id: Optional[UUID] = None,
        min_score: Optional[float] = None
    ) -> DashboardVesselsResponse:
        """Get ranked vessel candidates for attribution."""
        # Build query for attribution scores with vessel details
        query = select(
            AttributionScore.id,
            AttributionScore.vessel_id,
            AttributionScore.score,
            Vessel.mmsi,
            Vessel.name,
            AttributionScore.proximity_score,
            AttributionScore.temporality_score,
            AttributionScore.trajectory_score,
            AttributionScore.anomaly_score,
            AttributionScore.anomaly_flag
        ).select_from(
            AttributionScore.__table__
            .join(Vessel.__table__, AttributionScore.vessel_id == Vessel.id)
        )

        # Apply filters
        filters = []
        if incident_id:
            filters.append(AttributionScore.incident_id == incident_id)
        if min_score is not None:
            filters.append(AttributionScore.score >= min_score)

        if filters:
            query = query.where(and_(*filters))

        # Order by score descending (highest first)
        query = query.order_by(AttributionScore.score.desc())

        # Get total count
        count_query = select(func.count()).select_from(
            AttributionScore.__table__
            .join(Vessel.__table__, AttributionScore.vessel_id == Vessel.id)
        )
        if filters:
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Build response items with ranking
        items = []
        for rank, row in enumerate(rows, start=1):
            (
                score_id, vessel_id, score, mmsi, name,
                proximity_score, temporality_score, trajectory_score,
                anomaly_score, anomaly_flag
            ) = row

            # Determine confidence based on score
            if score >= 0.8:
                confidence_str = "HIGH"
            elif score >= 0.5:
                confidence_str = "MEDIUM"
            else:
                confidence_str = "LOW"

            # For distance and temporal match, we'll use proximity and temporality scores as proxies
            # In a real implementation, these might be calculated differently
            items.append(VesselCandidateItemResponse(
                vessel_id=vessel_id,
                name=name,
                rank=rank,
                attribution_score=float(score) if score is not None else 0.0,
                confidence=confidence_str,
                distance_to_origin_km=float(proximity_score) * 100 if proximity_score is not None else 0.0,  # Rough conversion
                temporal_match=float(temporality_score) if temporality_score is not None else 0.0
            ))

        return DashboardVesselsResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total
        )

    async def get_activity(
        self,
        limit: int = 50
    ) -> DashboardActivityResponse:
        """Get recent system activity."""
        # We'll create a unified activity feed from various sources
        # For now, we'll use incidents as the primary source of activity
        # In a full implementation, this would union multiple tables

        # Get recent incidents with their key events
        query = select(
            Incident.id,
            Incident.status,
            Incident.timestamp,
            literal('OIL_SPILL_DETECTED').label('event_type')
        ).select_from(Incident.__table__)

        # Order by timestamp descending
        query = query.order_by(Incident.timestamp.desc()).limit(limit)

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Build response items
        items = []
        for row in rows:
            incident_id, status, timestamp, event_type = row
            items.append(ActivityEventResponse(
                event=event_type,
                incident_id=incident_id,
                timestamp=timestamp.isoformat() if timestamp else ""
            ))

        return DashboardActivityResponse(items=items)

    async def get_investigation_details(self, investigation_id: UUID) -> Optional[InvestigationDetailResponse]:
        """Get complete investigation summary for dashboard."""
        # For this MVP, we'll reuse the existing investigation service logic
        # but simplify the response to match the dashboard PRD expectations

        # Import here to avoid circular dependencies
        from app.services.investigation_service import get_investigation_details as get_full_investigation

        # Get the full investigation details
        full_details = await get_full_investigation(self.db, investigation_id)
        if not full_details:
            return None

        # Transform to match dashboard expected format
        inc = full_details.get("incident") if isinstance(full_details, dict) else getattr(full_details, "incident", None)
        slick = full_details.get("slick") if isinstance(full_details, dict) else getattr(full_details, "slick", None)
        vessels = full_details.get("vessels", []) if isinstance(full_details, dict) else getattr(full_details, "vessels", [])
        attr_list = full_details.get("attribution", []) if isinstance(full_details, dict) else getattr(full_details, "attribution", [])
        evidence_val = full_details.get("evidence") if isinstance(full_details, dict) else getattr(full_details, "evidence", None)

        inc_dict = inc if isinstance(inc, dict) else {}
        slick_dict = slick if isinstance(slick, dict) else {}

        candidate_vessels = []
        for idx, (v, a) in enumerate(zip(vessels, attr_list)):
            v_dict = v if isinstance(v, dict) else {}
            a_dict = a if isinstance(a, dict) else {}
            score_val = a_dict.get("score", 0.0)
            candidate_vessels.append({
                "vessel_id": str(v_dict.get("id", "") or a_dict.get("vessel_id", "")),
                "mmsi": v_dict.get("mmsi") or a_dict.get("mmsi"),
                "name": v_dict.get("name") or a_dict.get("name"),
                "rank": idx + 1,
                "attribution_score": score_val,
                "confidence": "HIGH" if score_val >= 0.8 else "MEDIUM" if score_val >= 0.5 else "LOW",
                "distance_to_origin_km": 0.0,
                "temporal_match": a_dict.get("temporality", 0.0)
            })

        return InvestigationDetailResponse(
            investigation={
                "id": str(inc_dict.get("id", "")),
                "status": str(inc_dict.get("status", "OPEN"))
            },
            detection={
                "detected": bool(slick_dict.get("detected", False)),
                "confidence": float(slick_dict.get("confidence", 0.0)),
                "area_km2": float(slick_dict.get("area_km2", 0.0))
            },
            spill_regions=[],
            hindcast={},
            forecast={},
            ais_tracks=[],
            candidate_vessels=candidate_vessels,
            attribution={},
            evidence=[evidence_val] if evidence_val else []
        )