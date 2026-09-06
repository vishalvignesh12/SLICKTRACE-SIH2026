import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from sqlalchemy.orm import relationship
from app.core.database import Base

class SlickDetection(Base):
    __tablename__ = "slick_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("satellite_scenes.id", ondelete="SET NULL"), nullable=True)
    analysis_id = Column(String, nullable=True, index=True)  # Links to ML analysis job
    detected = Column(Boolean, nullable=False, default=True)  # Whether oil spill was detected
    confidence = Column(Float, nullable=False)  # 0 to 1
    model_version = Column(String, nullable=True, default="v1.0")  # Version of ML model used
    processing_time_ms = Column(Integer, nullable=True, default=0)  # Processing time in milliseconds
    source_scene_id = Column(String, nullable=True)  # Original scene ID from data provider
    geometry = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    area_km2 = Column(Float, nullable=False)
    length_km = Column(Float, nullable=True)
    width_km = Column(Float, nullable=True)
    orientation_deg = Column(Float, nullable=True)
    age_estimate_hours = Column(Float, nullable=True)
    age_confidence = Column(String, nullable=True) # HIGH, MEDIUM, LOW
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship to SpillRegion
    regions = relationship("SpillRegion", back_populates="detection", cascade="all, delete-orphan")
    # Relationship to Investigation
    investigation = relationship("Investigation", back_populates="detection")