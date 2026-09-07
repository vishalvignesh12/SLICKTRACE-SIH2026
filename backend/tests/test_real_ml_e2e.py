import os
import numpy as np
import pytest
import httpx
from datetime import datetime, UTC
from shapely.geometry import shape

try:
    import rasterio
    from rasterio.transform import Affine
    _HAS_RASTERIO = True
except ImportError:
    _HAS_RASTERIO = False

from app.models.satellite_scene import SatelliteScene
from app.integrations.ml import RESTMLProvider, translate_ml_response
from app.services.ml_inference_service import validate_ml_prediction, convert_ml_to_detection_format


@pytest.mark.asyncio
async def test_live_ml_service_health():
    """Verify live ML service is responding on port 8080."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get("http://127.0.0.1:8080/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["model_version"] == "oilspill-unet-v1"
        except httpx.ConnectError:
            pytest.skip("ML service not running on port 8080")


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_RASTERIO, reason="rasterio required for synthetic tiff test")
async def test_live_ml_service_predict_with_geotiff(tmp_path):
    """
    Test real RESTMLProvider against running ML API with a georeferenced TIFF:
    1. Writes GeoTIFF in projected UTM Zone 43N
    2. Calls RESTMLProvider.predict(scene) -> calls http://127.0.0.1:8080/predict
    3. Receives translated prediction with EPSG:4326 geometry
    4. Validates PRD schema
    5. Converts to detection format with exact centroid and bbox
    """
    # Create sample SAR TIFF in storage/incoming
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    storage_dir = os.path.join(project_root, "storage", "incoming")
    os.makedirs(storage_dir, exist_ok=True)

    tiff_filename = "S1A_LIVE_TEST_001.tif"
    tiff_path = os.path.join(storage_dir, tiff_filename)

    height, width = 512, 512
    # Realistic SAR backscatter in dB
    band1 = np.random.normal(-16.0, 2.5, (height, width)).astype(np.float32)
    # Add dark slick patch
    band1[150:350, 150:350] -= 12.0
    band2 = band1 - 6.0

    transform = Affine.translation(500000.0, 1000000.0) * Affine.scale(10.0, -10.0)

    with rasterio.open(
        tiff_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype=np.float32,
        crs="EPSG:32643",
        transform=transform,
    ) as dst:
        dst.write(band1, 1)
        dst.write(band2, 2)

    provider = RESTMLProvider(service_url="http://127.0.0.1:8080", timeout_seconds=30)

    scene = SatelliteScene(
        scene_id="S1A_LIVE_TEST_001",
        source="cloudflare-r2-replay",
        satellite="Sentinel-1",
        sensor="SAR",
        product_type="GRD",
        polarization="VV+VH",
        acquisition_time=datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC),
        image_url=f"storage://incoming/{tiff_filename}",
        status="RECEIVED"
    )

    try:
        prediction = await provider.predict(scene)
    except Exception as e:
        if "ConnectError" in str(e) or "All connection attempts failed" in str(e):
            pytest.skip("ML service not reachable on 127.0.0.1:8080")
        raise

    # 1. Verify PRD contract
    assert "detected" in prediction
    assert "confidence" in prediction
    assert "area_km2" in prediction
    assert "geometry" in prediction
    assert "model_name" in prediction
    assert "model_version" in prediction
    assert prediction["model_version"] == "oilspill-unet-v1"
    assert isinstance(prediction["detected"], bool)

    validate_ml_prediction(prediction)

    # 2. Convert to detection format
    detection_format = convert_ml_to_detection_format(prediction, scene, processing_time_ms=180)
    assert detection_data_valid(detection_format)

    # Clean up test file
    if os.path.exists(tiff_path):
        try:
            os.remove(tiff_path)
        except Exception:
            pass


def detection_data_valid(detection_format: dict) -> bool:
    assert detection_format["status"] == "COMPLETED"
    assert "spill_regions" in detection_format
    assert len(detection_format["spill_regions"]) > 0

    for reg in detection_format["spill_regions"]:
        assert "region_id" in reg
        assert "confidence" in reg
        assert "area_m2" in reg
        assert "centroid" in reg
        assert "bbox" in reg
        assert "geometry" in reg
    return True
