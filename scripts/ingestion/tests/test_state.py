"""
Unit tests for state.py
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from state import StateManager
from models import ProcessedObject


def test_state_manager_initialization():
    """Test StateManager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "test_state.json")
        manager = StateManager(state_file)

        assert str(manager.state_file) == state_file
        assert manager._state == {}  # Should start empty
        assert manager.count() == 0


def test_state_manager_loads_existing_file():
    """Test that StateManager loads existing state file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "test_state.json")

        # Create a test state file
        test_data = {
            "test/key.tif": {
                "object_key": "test/key.tif",
                "etag": "abc123",
                "scene_id": "S1A_TEST_001",
                "analysis_id": "test-analysis-id",
                "status": "SUCCESS",
                "timestamp": "2023-01-01T12:00:00+00:00",
                "error_message": None
            }
        }

        with open(state_file, 'w') as f:
            json.dump(test_data, f)

        # Load the state
        manager = StateManager(state_file)

        assert manager.count() == 1
        assert "test/key.tif" in manager._state
        obj = manager._state["test/key.tif"]
        assert isinstance(obj, ProcessedObject)
        assert obj.object_key == "test/key.tif"
        assert obj.etag == "abc123"
        assert obj.scene_id == "S1A_TEST_001"
        assert obj.status == "SUCCESS"


def test_state_manager_get_set_delete():
    """Test get, set, and delete operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "test_state.json")
        manager = StateManager(state_file)

        # Test get on non-existent key
        assert manager.get("nonexistent") is None

        # Test set
        obj = ProcessedObject(
            object_key="test/key.tif",
            etag="abc123",
            scene_id="S1A_TEST_001",
            status="PROCESSING"
        )
        manager.set("test/key.tif", obj)

        # Test get after set
        retrieved = manager.get("test/key.tif")
        assert retrieved is not None
        assert retrieved.object_key == "test/key.tif"
        assert retrieved.etag == "abc123"
        assert retrieved.scene_id == "S1A_TEST_001"
        assert retrieved.status == "PROCESSING"

        # Test exists
        assert manager.exists("test/key.tif") is True
        assert manager.exists("nonexistent") is False

        # Test delete
        manager.delete("test/key.tif")
        assert manager.get("test/key.tif") is None
        assert manager.exists("test/key.tif") is False

        # Test count
        assert manager.count() == 0


def test_state_manager_clear():
    """Test clearing all state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "test_state.json")
        manager = StateManager(state_file)

        # Add some objects
        obj1 = ProcessedObject(
            object_key="test/key1.tif",
            etag="abc123",
            scene_id="S1A_TEST_001"
        )
        obj2 = ProcessedObject(
            object_key="test/key2.tif",
            etag="def456",
            scene_id="S1A_TEST_002"
        )
        manager.set("test/key1.tif", obj1)
        manager.set("test/key2.tif", obj2)

        assert manager.count() == 2

        # Clear state
        manager.clear()
        assert manager.count() == 0
        assert manager.get("test/key1.tif") is None
        assert manager.get("test/key2.tif") is None


def test_state_manager_persistence():
    """Test that state persists to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "test_state.json")
        manager = StateManager(state_file)

        # Add an object
        obj = ProcessedObject(
            object_key="test/key.tif",
            etag="abc123",
            scene_id="S1A_TEST_001",
            analysis_id="test-analysis-id",
            status="SUCCESS"
        )
        manager.set("test/key.tif", obj)

        # Create a new manager instance pointing to the same file
        manager2 = StateManager(state_file)

        # Should have loaded the persisted state
        assert manager2.count() == 1
        retrieved = manager2.get("test/key.tif")
        assert retrieved is not None
        assert retrieved.object_key == "test/key.tif"
        assert retrieved.etag == "abc123"
        assert retrieved.scene_id == "S1A_TEST_001"
        assert retrieved.analysis_id == "test-analysis-id"
        assert retrieved.status == "SUCCESS"