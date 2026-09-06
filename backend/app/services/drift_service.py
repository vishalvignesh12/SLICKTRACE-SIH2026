import time
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from app.integrations.opendrift import FixtureDriftAdapter
from app.models.drift_result import DriftResult
from app.models.inference_log import MLInferenceLog
from app.schemas.drift import HindcastRequest, ForecastRequest
from app.core.logging import log_inference

async def calculate_hindcast(db: AsyncSession, req: HindcastRequest) -> DriftResult:
    """Calculate hindcast trajectory and probable origin point/time."""
    start_time = time.time()
    
    adapter = FixtureDriftAdapter()
    result = await adapter.run_hindcast(str(req.incident_id), req.slick_polygon.model_dump(), req.timestamp)
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Parse shapes
    origin_pt = from_shape(shape(result["origin_point"]), srid=4326) if result["origin_point"] else None
    prob_cone = from_shape(shape(result["origin_probability_cone"]), srid=4326) if result["origin_probability_cone"] else None
    hindcast_path = from_shape(shape(result["hindcast_path"]), srid=4326) if result["hindcast_path"] else None
    
    drift = DriftResult(
        incident_id=req.incident_id,
        origin_point=origin_pt,
        origin_probability_cone=prob_cone,
        origin_time_estimate=result["origin_time_estimate"],
        origin_confidence=result["origin_confidence"],
        hindcast_path=hindcast_path,
        forecast_path=None,
        model_name="OpenDrift-Lagrangian",
        model_version="v1.10.4"
    )
    db.add(drift)
    
    # Save ML Inference Log
    log = MLInferenceLog(
        service_name="drift_service_hindcast",
        request_payload={"incident_id": str(req.incident_id), "timestamp": req.timestamp.isoformat()},
        response_payload={
            "origin_time_estimate": result["origin_time_estimate"].isoformat() if result["origin_time_estimate"] else None,
            "origin_confidence": result["origin_confidence"]
        },
        model_name="OpenDrift-Lagrangian",
        model_version="v1.10.4",
        latency_ms=latency_ms,
        status="SUCCESS",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    await db.commit()
    await db.refresh(drift)
    
    log_inference(
        service_name="drift_service_hindcast",
        model_name="OpenDrift-Lagrangian",
        model_version="v1.10.4",
        analysis_id="unknown",
        incident_id=str(req.incident_id),
        latency_ms=latency_ms,
        status_code=200
    )
    
    return drift

async def calculate_forecast(db: AsyncSession, req: ForecastRequest) -> DriftResult:
    """Calculate forecast trajectory for the slick's future movement."""
    start_time = time.time()
    
    adapter = FixtureDriftAdapter()
    result = await adapter.run_forecast(str(req.incident_id), req.slick_polygon.model_dump(), req.timestamp)
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Parse shape
    forecast_path = from_shape(shape(result["forward_path"]), srid=4326) if result["forward_path"] else None
    
    drift = DriftResult(
        incident_id=req.incident_id,
        origin_point=None,
        origin_probability_cone=None,
        origin_time_estimate=None,
        origin_confidence=None,
        hindcast_path=None,
        forecast_path=forecast_path,
        model_name="OpenDrift-Lagrangian",
        model_version="v1.10.4"
    )
    db.add(drift)
    
    # Save ML Inference Log
    log = MLInferenceLog(
        service_name="drift_service_forecast",
        request_payload={"incident_id": str(req.incident_id), "timestamp": req.timestamp.isoformat()},
        response_payload={
            "forecast_path_registered": True
        },
        model_name="OpenDrift-Lagrangian",
        model_version="v1.10.4",
        latency_ms=latency_ms,
        status="SUCCESS",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    await db.commit()
    await db.refresh(drift)
    
    log_inference(
        service_name="drift_service_forecast",
        model_name="OpenDrift-Lagrangian",
        model_version="v1.10.4",
        analysis_id="unknown",
        incident_id=str(req.incident_id),
        latency_ms=latency_ms,
        status_code=200
    )
    
    return drift
