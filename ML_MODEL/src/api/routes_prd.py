"""
PRD-compatible inference API for backend integration.
Receives a scene reference, runs the predictor, and returns PRD-format result.
"""
import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from src.inference.predictor import OilSpillPredictor
from src.schemas.prediction import PredictionResult, SpillRegion
import json

app = FastAPI(title="Oil Spill Segmentation Inference Service (PRD Compatible)")

CHECKPOINT_PATH = os.environ.get("OILSPILL_CHECKPOINT", "models/oilspill-v1/best.pt")
_predictor: OilSpillPredictor | None = None


def get_predictor() -> OilSpillPredictor:
    global _predictor
    if _predictor is None:
        if not os.path.exists(CHECKPOINT_PATH):
            raise HTTPException(status_code=503, detail=f"checkpoint not found at {CHECKPOINT_PATH}")
        _predictor = OilSpillPredictor(CHECKPOINT_PATH)
    return _predictor


class PredictRequest(BaseModel):
    scene_id: str
    image_uri: str  # e.g. "storage://.../scene.tif" or a local/mounted path
    acquisition_time: Optional[str] = None
    threshold: float = 0.5


class PRDPredictionResponse(BaseModel):
    scene_id: str
    status: str
    oil_spill_detected: bool
    confidence: float
    area_km2: float
    geometry: Dict[str, Any]
    model_name: str
    model_version: str
    processing_time_ms: int
    spill_regions: List[Dict[str, Any]] = []


@app.get("/health")
def health():
    try:
        predictor = get_predictor()
        return {"status": "ok", "model_version": "oilspill-unet-v1"}
    except HTTPException:
        return {"status": "model_not_loaded"}


@app.post("/predict", response_model=PRDPredictionResponse)
def predict(req: PredictRequest):
    start_time = time.time()
    predictor = get_predictor()

    # In production, image_uri resolves via the configured storage layer
    # (e.g. S3/GCS/local mount); here we assume it's a locally reachable path.
    image_path = req.image_uri.replace("storage://", "/mnt/storage/")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"image not found: {image_path}")

    # Run prediction
    result: PredictionResult = predictor.predict(
        image_path,
        scene_id=req.scene_id,
        acquisition_time=req.acquisition_time,
        threshold=req.threshold,
        low_thr=0.3,
        high_thr=0.6,
    )

    processing_time_ms = int((time.time() - start_time) * 1000)

    # Convert to PRD format
    # Use present_regions for spill regions (high confidence detections)
    spill_regions = result.present_regions if result.present_regions else result.regions

    # Calculate total area and create geometry from regions
    total_area_m2 = 0.0
    geometry = {"type": "Polygon", "coordinates": [[[0, 0], [0, 0], [0, 0]]]}  # Default invalid geometry

    if spill_regions:
        # Use the first region's geometry as the overall detection geometry
        # In a more sophisticated implementation, we might union all regions
        first_region = spill_regions[0]
        if first_region.polygon_geojson_geo:
            geometry = first_region.polygon_geojson_geo
        elif first_region.polygon_geojson_pixel:
            # Convert pixel coordinates to geo if needed (simplified)
            geometry = first_region.polygon_geojson_pixel

        # Sum up areas
        for region in spill_regions:
            if region.area_m2_approx is not None:
                total_area_m2 += region.area_m2_approx
            # Fallback: if we only have pixel area, we'd need geotransform to convert
            # For now, we'll approximate or skip if not available

    # Format spill regions for PRD response
    formatted_spill_regions = []
    for i, region in enumerate(spill_regions):
        region_confidence = result.max_confidence  # Use overall confidence or could be region-specific
        region_area_m2 = region.area_m2_approx if region.area_m2_approx is not None else 0.0

        # Create centroid
        centroid = {"lat": 0.0, "lon": 0.0}
        if region.centroid_geo:
            centroid = {"lat": region.centroid_geo[1], "lon": region.centroid_geo[0]}  # Note: geo is (lat, lon) or (lon, lat)?
        elif region.centroid_px:
            # Would need geotransform to convert pixel to geo - simplified fallback
            centroid = {"lat": float(region.centroid_px[1]), "lon": float(region.centroid_px[0])}

        # Create bounding box (simplified - would need actual calculation from polygon)
        bbox = {
            "min_lat": centroid["lat"] - 0.01,
            "min_lon": centroid["lon"] - 0.01,
            "max_lat": centroid["lat"] + 0.01,
            "max_lon": centroid["lon"] + 0.01
        }

        formatted_spill_regions.append({
            "region_id": f"spill_{i:03d}",
            "confidence": float(region_confidence),
            "area_m2": int(region_area_m2),
            "centroid": centroid,
            "bbox": bbox,
            "polygon_uri": None,  # Would be set if we saved to storage
            "mask_uri": None      # Would be set if we saved to storage
        })

    return PRDPredictionResponse(
        scene_id=result.scene_id,
        status="COMPLETED",
        oil_spill_detected=result.presence,
        confidence=float(result.max_confidence),
        area_km2=total_area_m2 / 1_000_000.0,  # Convert m² to km²
        geometry=geometry,
        model_name="oilspill-unet",
        model_version=result.model_version,
        processing_time_ms=processing_time_ms,
        spill_regions=formatted_spill_regions
    )