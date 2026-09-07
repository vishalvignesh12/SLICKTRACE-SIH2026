"""
Minimal inference API (PRD §6, Phase 7). Receives a scene reference (not the
raw image bytes), retrieves the image from local/mounted storage, runs the
predictor, and returns the structured result for the backend to persist.

Run: uvicorn src.api.routes:app --host 0.0.0.0 --port 8080
"""
import os
import logging
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from src.inference.predictor import OilSpillPredictor
from src.storage.resolver import resolve_image_path

logger = logging.getLogger("ml_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Oil Spill Segmentation Inference Service")

CHECKPOINT_PATH = os.environ.get("OILSPILL_CHECKPOINT", "models/oilspill-v1/best.pt")
_predictor: OilSpillPredictor | None = None


def get_predictor() -> OilSpillPredictor:
    global _predictor
    if _predictor is None:
        # Check relative to working dir or ML_MODEL root
        ckpt_cand = CHECKPOINT_PATH
        if not os.path.exists(ckpt_cand):
            alt_cand = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), CHECKPOINT_PATH)
            if os.path.exists(alt_cand):
                ckpt_cand = alt_cand
        if not os.path.exists(ckpt_cand):
            raise HTTPException(status_code=503, detail=f"checkpoint not found at {CHECKPOINT_PATH}")
        _predictor = OilSpillPredictor(ckpt_cand)
    return _predictor


class PredictRequest(BaseModel):
    scene_id: str
    image_uri: str  # e.g. "storage://incoming/scene.tif", local path, or R2 public URL
    acquisition_time: str | None = None
    threshold: float = 0.5


class HealthResponse(BaseModel):
    status: str
    model_version: str | None = None


@app.get("/health", response_model=HealthResponse)
def health():
    try:
        predictor = get_predictor()
        return HealthResponse(status="ok", model_version="oilspill-unet-v1")
    except HTTPException:
        return HealthResponse(status="model_not_loaded")


@app.post("/predict")
def predict(req: PredictRequest):
    predictor = get_predictor()

    try:
        image_path = resolve_image_path(req.image_uri)
    except ValueError as e:
        logger.warning(f"Invalid image URI request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError as e:
        logger.warning(f"Image not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resolving image URI '{req.image_uri}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve image URI: {str(e)}"
        )

    try:
        result = predictor.predict(
            image_path,
            scene_id=req.scene_id,
            acquisition_time=req.acquisition_time,
            threshold=req.threshold,
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"Inference error on {image_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference prediction failed: {str(e)}"
        )
