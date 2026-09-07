"""
Unit tests for metadata.py
"""
import json
from datetime import datetime, timezone
from metadata import validate_metadata_file, load_metadata_file
from models import SceneMetadata


def test_validate_metadata_file_valid():
    """Test validation of valid metadata."""
    metadata_dict = {
        "scene_id": "S1A_TEST_001",
        "satellite": "Sentinel-1A",
        "sensor": "SAR",
        "product_type": "GRD",
        "polarization": "VV",
        "acquisition_time": datetime.now(timezone.utc),
        "processing_time": datetime.now(timezone.utc),
        "bbox": {
            "type": "Polygon",
            "coordinates": [[
                [10.0, 50.0],
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5],
                [10.0, 50.0]
            ]]
        },
        "scene_metadata": {
            "orbit_direction": "DESCENDING",
            "resolution": "10m"
        }
    }

    # This should not raise an exception
    result = validate_metadata_file(metadata_dict)
    assert isinstance(result, SceneMetadata)
    assert result.scene_id == "S1A_TEST_001"
    assert result.satellite == "Sentinel-1A"
    assert result.product_type == "GRD"


def test_validate_metadata_file_missing_required_field():
    """Test validation fails with missing required field."""
    metadata_dict = {
        # Missing scene_id
        "satellite": "Sentinel-1A",
        "sensor": "SAR",
        "product_type": "GRD",
        "polarization": "VV",
        "acquisition_time": datetime.now(timezone.utc),
        "bbox": {
            "type": "Polygon",
            "coordinates": [[
                [10.0, 50.0],
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5],
                [10.0, 50.0]
            ]]
        }
    }

    try:
        validate_metadata_file(metadata_dict)
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "scene_id" in str(e).lower() or "field required" in str(e).lower()


def test_validate_metadata_file_invalid_bbox():
    """Test validation fails with invalid bbox."""
    metadata_dict = {
        "scene_id": "S1A_TEST_001",
        "satellite": "Sentinel-1A",
        "sensor": "SAR",
        "product_type": "GRD",
        "polarization": "VV",
        "acquisition_time": datetime.now(timezone.utc),
        "bbox": {
            "type": "Polygon",
            "coordinates": [[
                [10.0, 50.0],
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5]
                # Missing closing coordinate - not a closed ring
            ]]
        }
    }

    try:
        validate_metadata_file(metadata_dict)
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "closed" in str(e).lower() or "coordinate" in str(e).lower()


def test_validate_metadata_file_invalid_coordinates():
    """Test validation fails with invalid coordinate values."""
    metadata_dict = {
        "scene_id": "S1A_TEST_001",
        "satellite": "Sentinel-1A",
        "sensor": "SAR",
        "product_type": "GRD",
        "polarization": "VV",
        "acquisition_time": datetime.now(timezone.utc),
        "bbox": {
            "type": "Polygon",
            "coordinates": [[
                [200.0, 50.0],  # Invalid longitude (> 180)
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5],
                [200.0, 50.0]   # Close the ring
            ]]
        }
    }

    try:
        validate_metadata_file(metadata_dict)
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "longitude" in str(e).lower() or "-180" in str(e) or "180" in str(e)


def test_load_metadata_file_valid_json():
    """Test loading valid JSON metadata."""
    metadata_json = json.dumps({
        "scene_id": "S1A_TEST_001",
        "satellite": "Sentinel-1A",
        "sensor": "SAR",
        "product_type": "GRD",
        "polarization": "VV",
        "acquisition_time": datetime.now(timezone.utc).isoformat(),
        "processing_time": datetime.now(timezone.utc).isoformat(),
        "bbox": {
            "type": "Polygon",
            "coordinates": [[
                [10.0, 50.0],
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5],
                [10.0, 50.0]
            ]]
        }
    })

    result = load_metadata_file("test-object-key", metadata_json)
    assert isinstance(result, SceneMetadata)
    assert result.scene_id == "S1A_TEST_001"


def test_load_metadata_file_invalid_json():
    """Test loading invalid JSON metadata."""
    invalid_json = "{ not valid json"

    try:
        load_metadata_file("test-object-key", invalid_json)
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "invalid json" in str(e).lower() or "jsondecodeerror" in str(e).lower()