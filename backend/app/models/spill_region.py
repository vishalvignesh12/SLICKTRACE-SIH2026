import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.slick_detection import SlickDetection


class SpillRegion(Base):
    __tablename__ = "spill_regions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("slick_detections.id", ondelete="CASCADE"), nullable=False)
    region_index = Column(Integer, nullable=False)  # Index of region within detection
    geometry = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    area_m2 = Column(Float, nullable=False)  # Area in square meters
    perimeter_m = Column(Float, nullable=True)  # Perimeter in meters
    # Note: Centroid and bounding box are computed properties, not stored as separate columns
    # They can be calculated from geometry when needed
    confidence = Column(Float, nullable=False)  # 0 to 1
    mask_uri = Column(String, nullable=True)  # URI to region-specific mask in object storage
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship to SlickDetection
    detection = relationship("SlickDetection", back_populates="regions")