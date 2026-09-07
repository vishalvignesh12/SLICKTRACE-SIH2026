import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.models.satellite_scene import SatelliteScene
from app.integrations.ml import RESTMLProvider, translate_ml_response, FixtureMLProvider, get_ml_provider
from app.services.ml_inference_service import validate_ml_prediction, convert_ml_to_detection_format


@pytest.fixture
def sample_scene():
    return SatelliteScene(
        scene_id="S1A_TEST_SCENE_001",
        source="sentinel-1-replay",
        satellite="Sentinel-1",
        sensor="SAR",
        product_type="GRD",
        polarization="VV",
        acquisition_time=datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
        image_url="storage://incoming/S1A_TEST_SCENE_001.tif",
        status="RECEIVED"
    )


def test_translate_ml_response_detected(sample_scene):
    raw_ml_output = {
        "scene_id": "S1A_TEST_SCENE_001",
        "model_version": "oilspill-unet-v1",
        "presence": True,
        "max_confidence": 0.92,
        "regions": [],
        "present_regions": [
            {
                "centroid_px": (128.0, 128.0),
                "area_px2": 1500.0,
                "polygon_geojson_pixel": {
                    "type": "Polygon",
                    "coordinates": [[[100, 100], [150, 100], [150, 150], [100, 150], [100, 100]]]
                },
                "centroid_geo": (75.123, 9.456),
                "area_m2_approx": 150000.0,
                "polygon_geojson_geo": {
                    "type": "Polygon",
                    "coordinates": [
                        [[75.10, 9.40], [75.15, 9.40], [75.15, 9.50], [75.10, 9.50], [75.10, 9.40]]
                    ]
                }
            }
        ],
        "likely_regions": [],
        "acquisition_time": "2026-06-15T12:00:00Z"
    }

    translated = translate_ml_response(raw_ml_output, sample_scene)

    assert translated["detected"] is True
    assert translated["confidence"] == 0.92
    assert translated["model_name"] == "oilspill-unet"
    assert translated["model_version"] == "oilspill-unet-v1"
    assert translated["area_km2"] == 0.15
    assert translated["geometry"]["type"] == "Polygon"
    assert len(translated["geometry"]["coordinates"][0]) == 5
    assert len(translated["spill_regions"]) == 1
    assert translated["spill_regions"][0]["centroid"]["lon"] == 75.123
    assert translated["spill_regions"][0]["centroid"]["lat"] == 9.456

    # Verify validation passes
    validate_ml_prediction(translated)


def test_translate_ml_response_no_spill(sample_scene):
    raw_ml_output = {
        "scene_id": "S1A_TEST_SCENE_002",
        "model_version": "oilspill-unet-v1",
        "presence": False,
        "max_confidence": 0.12,
        "regions": [],
        "present_regions": [],
        "likely_regions": [],
        "acquisition_time": "2026-06-15T12:00:00Z"
    }

    translated = translate_ml_response(raw_ml_output, sample_scene)

    assert translated["detected"] is False
    assert translated["confidence"] == 0.12
    assert translated["area_km2"] == 0.0
    assert translated["geometry"]["type"] == "Polygon"

    validate_ml_prediction(translated)


def test_convert_ml_to_detection_format_preserves_attributes(sample_scene):
    ml_prediction = {
        "detected": True,
        "confidence": 0.88,
        "area_km2": 0.25,
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[75.10, 9.40], [75.15, 9.40], [75.15, 9.50], [75.10, 9.50], [75.10, 9.40]]
            ]
        },
        "model_name": "oilspill-unet",
        "model_version": "oilspill-unet-v1",
        "length_km": 11.2,
        "width_km": 5.5,
        "orientation_deg": 45.0,
        "age_estimate_hours": 12.0,
        "age_confidence": "HIGH"
    }

    converted = convert_ml_to_detection_format(ml_prediction, sample_scene, processing_time_ms=120)

    assert converted["oil_spill_detected"] is True
    assert converted["confidence"] == 0.88
    assert converted["model_version"] == "oilspill-unet-v1"
    assert len(converted["spill_regions"]) == 1

    region = converted["spill_regions"][0]
    # Check that centroid and bbox are calculated and NOT 0,0
    assert 75.0 <= region["centroid"]["lon"] <= 75.2
    assert 9.3 <= region["centroid"]["lat"] <= 9.6
    assert region["bbox"]["min_lon"] == 75.10
    assert region["bbox"]["max_lat"] == 9.50


def test_convert_ml_to_detection_format_no_spill_empty_regions(sample_scene):
    ml_prediction = {
        "detected": False,
        "confidence": 0.35,
        "area_km2": 0.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]]
        },
        "model_name": "oilspill-unet",
        "model_version": "oilspill-unet-v1",
        "length_km": None,
        "width_km": None,
        "orientation_deg": None,
        "age_estimate_hours": None,
        "age_confidence": None,
        "spill_regions": []
    }

    converted = convert_ml_to_detection_format(ml_prediction, sample_scene, processing_time_ms=50)

    assert converted["oil_spill_detected"] is False
    assert converted["confidence"] == 0.35
    assert converted["model_version"] == "oilspill-unet-v1"
    assert converted["spill_regions"] == []  # MUST remain empty for non-detected scenes



@pytest.mark.asyncio
async def test_rest_ml_provider_success(sample_scene):
    mock_ml_response = {
        "scene_id": "S1A_TEST_SCENE_001",
        "model_version": "oilspill-unet-v1",
        "presence": True,
        "max_confidence": 0.95,
        "regions": [],
        "present_regions": [
            {
                "centroid_px": (100.0, 100.0),
                "area_px2": 2000.0,
                "polygon_geojson_pixel": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
                "centroid_geo": (88.1, 14.2),
                "area_m2_approx": 200000.0,
                "polygon_geojson_geo": {
                    "type": "Polygon",
                    "coordinates": [[[88.0, 14.0], [88.2, 14.0], [88.2, 14.3], [88.0, 14.3], [88.0, 14.0]]]
                }
            }
        ],
        "likely_regions": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_ml_response
    mock_resp.raise_for_status = MagicMock()

    provider = RESTMLProvider("http://localhost:8080")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.predict(sample_scene)

        assert result["detected"] is True
        assert result["confidence"] == 0.95
        assert result["area_km2"] == 0.2
        assert result["model_version"] == "oilspill-unet-v1"

        # Verify request payload sent to ML API
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["scene_id"] == "S1A_TEST_SCENE_001"
        assert call_kwargs["json"]["image_uri"] == "storage://incoming/S1A_TEST_SCENE_001.tif"


@pytest.mark.asyncio
async def test_rest_ml_provider_timeout(sample_scene):
    provider = RESTMLProvider("http://localhost:8080", timeout_seconds=1)

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(Exception, match="timed out"):
            await provider.predict(sample_scene)
