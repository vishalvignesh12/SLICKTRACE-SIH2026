from datetime import datetime
from typing import Optional, List, Literal, Tuple
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.scene import GeoJSONPolygon

class GeoJSONPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: Tuple[float, float] # [longitude, latitude]

class IncidentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    timestamp: datetime
    location: GeoJSONPoint
    status: str = "DETECTED"

class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    timestamp: datetime
    location: GeoJSONPoint
    status: str
    created_at: datetime
    updated_at: datetime
    slick_polygon: Optional[GeoJSONPolygon] = None
    area_km2: Optional[float] = None
    length_km: Optional[float] = None
    width_km: Optional[float] = None
    confidence: Optional[float] = None
    source_scene_id: Optional[str] = None
