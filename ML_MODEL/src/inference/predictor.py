"""
Single-scene inference: raw SAR TIFF -> PredictionResult (PRD Phase 7 core logic).

Usage:
    python -m src.inference.predictor --checkpoint models/oilspill-v1/best.pt --image scene.tif
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import torch

from src.models.unet import UNet
from src.postprocessing.mask import label_regions, threshold_and_clean
from src.postprocessing.polygon import mask_to_polygons
from src.preprocessing.normalize import normalize_sar
from src.preprocessing.tiling import make_tiles, stitch_predictions
from src.schemas.prediction import PredictionResult, SpillRegion

try:
    import rasterio
    _HAS_RASTERIO = True
except ImportError:
    _HAS_RASTERIO = False

import tifffile

MODEL_VERSION = "oilspill-unet-v1"


class OilSpillPredictor:
    def __init__(self, checkpoint_path: str, device: str | None = None, tile_size: int = 512, overlap: int = 64):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        ckpt = torch.load(checkpoint_path, map_location=self.device)
        self.model = UNet(in_channels=2, num_classes=1).to(self.device)
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()
        self.tile_size = tile_size
        self.overlap = overlap

    def _read_image(self, path: str):
        transform = None
        crs = None
        if path.lower().endswith((".tif", ".tiff")) and _HAS_RASTERIO:
            try:
                with rasterio.open(path) as src:
                    arr = src.read().astype(np.float32)  # (bands, H, W)
                    if src.transform is not None:
                        transform = src.transform
                    if src.crs is not None:
                        crs = src.crs
            except Exception:
                arr = tifffile.imread(path).astype(np.float32)
                if arr.ndim == 3:
                    arr = np.transpose(arr, (2, 0, 1))
        else:
            arr = tifffile.imread(path).astype(np.float32)
            if arr.ndim == 3:
                arr = np.transpose(arr, (2, 0, 1))

        if arr.shape[0] == 1:
            arr = arr.repeat(2, axis=0)
        return arr[:2], transform, crs

    @torch.no_grad()
    def predict(
        self,
        image_path: str,
        scene_id: str | None = None,
        acquisition_time: str | None = None,
        threshold: float = 0.5,
        low_thr: float = 0.3,
        high_thr: float = 0.6,
        min_area_px: int = 50,
    ) -> PredictionResult:
        raw, transform, crs = self._read_image(image_path)
        h, w = raw.shape[1], raw.shape[2]
        normed = normalize_sar(raw)

        tiles, offsets = make_tiles(normed, self.tile_size, self.overlap)
        probs = []
        for tile in tiles:
            x = torch.from_numpy(tile).unsqueeze(0).float().to(self.device)
            logits = self.model(x)
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
            probs.append(prob)

        full_prob = stitch_predictions(probs, offsets, (h, w), self.tile_size)

        # Compute three masks based on thresholds
        absent_mask = (full_prob < low_thr).astype(np.uint8)
        present_mask = (full_prob >= high_thr).astype(np.uint8)
        likely_mask = ((full_prob >= low_thr) & (full_prob < high_thr)).astype(np.uint8)

        # Convert each mask to region polygons (with CRS conversion to EPSG:4326)
        present_regions = [
            SpillRegion(**poly) for poly in mask_to_polygons(present_mask, transform, crs)
        ]
        likely_regions = [
            SpillRegion(**poly) for poly in mask_to_polygons(likely_mask, transform, crs)
        ]

        max_conf = float(full_prob.max()) if full_prob.size else 0.0
        return PredictionResult(
            scene_id=scene_id or os.path.basename(image_path),
            model_version=MODEL_VERSION,
            presence=len(present_regions) > 0,
            max_confidence=max_conf,
            regions=present_regions,  # legacy field
            present_regions=present_regions,
            likely_regions=likely_regions,
            acquisition_time=acquisition_time,
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--low_thr", type=float, default=0.3, help="lower confidence threshold for absent/present split")
    p.add_argument("--high_thr", type=float, default=0.6, help="upper confidence threshold for present class")
    p.add_argument("--out", default=None, help="optional path to write JSON result")
    args = p.parse_args()

    predictor = OilSpillPredictor(args.checkpoint)
    result = predictor.predict(
        args.image,
        threshold=args.threshold,
        low_thr=args.low_thr,
        high_thr=args.high_thr,
    )
    output = json.dumps(result.to_dict(), indent=2)
    print(output)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
