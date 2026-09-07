import os
import tempfile
import numpy as np
import pytest
from fastapi.testclient import TestClient

try:
    import rasterio
    from rasterio.transform import Affine
    _HAS_RASTERIO = True
except ImportError:
    _HAS_RASTERIO = False

from src.api.routes import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "model_not_loaded")


def test_predict_missing_image_404(client):
    response = client.post(
        "/predict",
        json={
            "scene_id": "missing_scene_123",
            "image_uri": "storage://incoming/non_existent_image_12345.tif",
            "threshold": 0.5
        }
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_predict_ssrf_attempt_400(client):
    response = client.post(
        "/predict",
        json={
            "scene_id": "malicious_scene",
            "image_uri": "http://169.254.169.254/latest/meta-data/",
            "threshold": 0.5
        }
    )
    assert response.status_code == 400
    assert "security error" in response.json()["detail"].lower()


@pytest.mark.skipif(not _HAS_RASTERIO, reason="rasterio required for synthetic tiff test")
def test_predict_synthetic_georeferenced_tiff(client, tmp_path, monkeypatch):
    # Create synthetic 2-band SAR GeoTIFF
    tiff_path = tmp_path / "synthetic_sar.tif"
    height, width = 256, 256
    band1 = np.random.uniform(-25, 0, (height, width)).astype(np.float32)
    band2 = np.random.uniform(-30, -5, (height, width)).astype(np.float32)

    transform = Affine.translation(75.0, 10.0) * Affine.scale(0.001, -0.001)

    with rasterio.open(
        str(tiff_path),
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype=np.float32,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(band1, 1)
        dst.write(band2, 2)

    response = client.post(
        "/predict",
        json={
            "scene_id": "test_synthetic_scene_001",
            "image_uri": str(tiff_path),
            "acquisition_time": "2026-06-15T12:00:00Z",
            "threshold": 0.5
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "scene_id" in data
    assert "model_version" in data
    assert "presence" in data
    assert "max_confidence" in data
    assert "regions" in data
    assert "present_regions" in data
    assert "likely_regions" in data
    assert isinstance(data["presence"], bool)
    assert 0.0 <= data["max_confidence"] <= 1.0
