from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.scene import GeoJSONPolygon

class AnalyzeRequest(BaseModel):
    scene_id: str
    image_url: Optional[str] = None
    timestamp: datetime

class DetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detection_id: UUID
    incident_id: Optional[UUID] = None
    source_scene_id: Optional[str] = None
    slick_polygon: GeoJSONPolygon
    area_km2: float
    length_km: Optional[float] = None
    width_km: Optional[float] = None
    orientation_deg: Optional[float] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    age_estimate_hours: Optional[float] = None
    age_confidence: Optional[str] = None # HIGH, MEDIUM, LOW
