"""
Unit tests for models.py
"""
from datetime import datetime, timezone
from models import SceneMetadata, ProcessedObject


def test_scene_metadata_creation():
    """Test creating a SceneMetadata object."""
    metadata = SceneMetadata(
        scene_id="S1A_TEST_001",
        satellite="Sentinel-1A",
        sensor="SAR",
        product_type="GRD",
        polarization="VV",
        acquisition_time=datetime.now(timezone.utc),
        processing_time=datetime.now(timezone.utc),
        bbox={
            "type": "Polygon",
            "coordinates": [[
                [10.0, 50.0],
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5],
                [10.0, 50.0]
            ]]
        }
    )

    assert metadata.scene_id == "S1A_TEST_001"
    assert metadata.satellite == "Sentinel-1A"
    assert metadata.product_type == "GRD"
    assert metadata.polarization == "VV"
    assert metadata.bbox["type"] == "Polygon"


def test_scene_metadata_optional_fields():
    """Test SceneMetadata with optional fields as None."""
    metadata = SceneMetadata(
        scene_id="S1A_TEST_001",
        satellite="Sentinel-1A",
        sensor=None,  # Optional
        product_type="GRD",
        polarization=None,  # Optional
        acquisition_time=datetime.now(timezone.utc),
        processing_time=None,  # Optional
        bbox={
            "type": "Polygon",
            "coordinates": [[
                [10.0, 50.0],
                [10.5, 50.0],
                [10.5, 50.5],
                [10.0, 50.5],
                [10.0, 50.0]
            ]]
        },
        scene_metadata=None  # Optional
    )

    assert metadata.sensor is None
    assert metadata.polarization is None
    assert metadata.processing_time is None
    assert metadata.scene_metadata is None


def test_processed_object_creation():
    """Test creating a ProcessedObject."""
    now = datetime.now(timezone.utc)
    obj = ProcessedObject(
        object_key="test/key.tif",
        etag="abc123",
        scene_id="S1A_TEST_001",
        analysis_id="test-analysis-id",
        status="SUCCESS",
        timestamp=now
    )

    assert obj.object_key == "test/key.tif"
    assert obj.etag == "abc123"
    assert obj.scene_id == "S1A_TEST_001"
    assert obj.analysis_id == "test-analysis-id"
    assert obj.status == "SUCCESS"
    assert obj.timestamp == now


def test_processed_object_defaults():
    """Test ProcessedObject with default values."""
    obj = ProcessedObject(
        object_key="test/key.tif",
        etag="abc123",
        scene_id="S1A_TEST_001"
    )

    assert obj.object_key == "test/key.tif"
    assert obj.etag == "abc123"
    assert obj.scene_id == "S1A_TEST_001"
    assert obj.analysis_id is None
    assert obj.status == "PENDING"  # Default value
    assert obj.timestamp is not None  # Should be set automatically
    assert obj.error_message is None


def test_processed_object_json_encoding():
    """Test that ProcessedObject handles datetime JSON encoding."""
    now = datetime.now(timezone.utc)
    obj = ProcessedObject(
        object_key="test/key.tif",
        etag="abc123",
        scene_id="S1A_TEST_001",
        timestamp=now
    )

    # This should not raise an exception
    json_data = obj.model_dump_json()
    import json
    parsed = json.loads(json_data)
    assert parsed["object_key"] == "test/key.tif"
    assert parsed["scene_id"] == "S1A_TEST_001"
    # Timestamp should be ISO format string
    assert "T" in parsed["timestamp"] and ("Z" in parsed["timestamp"] or "+" in parsed["timestamp"])