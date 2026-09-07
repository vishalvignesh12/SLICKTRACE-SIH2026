"""
Data models for R2 Ingestion Worker
Defines typed structures for metadata and state tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class SceneMetadata(BaseModel):
    """Metadata for a satellite scene."""
    scene_id: str = Field(..., min_length=1)
    satellite: str = Field(..., min_length=1)
    sensor: Optional[str] = None
    product_type: str = Field(..., min_length=1)
    polarization: Optional[str] = None
    acquisition_time: datetime
    processing_time: Optional[datetime] = None
    bbox: Dict[str, Any]  # GeoJSON Polygon
    scene_metadata: Optional[Dict[str, Any]] = None

    @validator('bbox')
    def validate_bbox(cls, v):
        """Validate that bbox is a valid GeoJSON Polygon."""
        if not isinstance(v, dict) or v.get('type') != 'Polygon':
            raise ValueError('bbox must be a GeoJSON Polygon')

        coordinates = v.get('coordinates', [])
        if not isinstance(coordinates, list) or len(coordinates) == 0:
            raise ValueError('bbox must contain at least one coordinate ring')

        # Validate each ring
        for i, ring in enumerate(coordinates):
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError(f'bbox coordinate ring {i} must have at least 4 points')

            # Check if ring is closed (first point == last point)
            if len(ring) >= 4 and ring[0] != ring[-1]:
                raise ValueError(f'bbox coordinate ring {i} must be closed (first point == last point)')

            # Validate each coordinate
            for j, coord in enumerate(ring):
                if not isinstance(coord, list) or len(coord) != 2:
                    raise ValueError(f'bbox coordinate {i},{j} must be [longitude, latitude]')

                lon, lat = coord
                if not (-180 <= lon <= 180):
                    raise ValueError(f'bbox coordinate {i},{j} longitude {lon} must be between -180 and 180')
                if not (-90 <= lat <= 90):
                    raise ValueError(f'bbox coordinate {i},{j} latitude {lat} must be between -90 and 90')

        return v


class ProcessedObject(BaseModel):
    """Tracking information for a processed R2 object."""
    object_key: str
    etag: str
    scene_id: str
    analysis_id: Optional[str] = None
    status: str = "PENDING"  # PENDING, SUCCESS, DUPLICATE, FAILED
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }