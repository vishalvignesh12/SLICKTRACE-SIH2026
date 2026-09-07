"""
State management for R2 Ingestion Worker
Tracks processed objects to prevent reprocessing.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from models import ProcessedObject
from logger import setup_logger

logger = setup_logger(__name__)


class StateManager:
    """Manages state of processed R2 objects."""

    def __init__(self, state_file: str = "scripts/ingestion/state/processed.json"):
        """
        Initialize state manager.

        Args:
            state_file: Path to state JSON file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, ProcessedObject] = {}
        self.load()

    def load(self) -> None:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self._state = {
                        key: ProcessedObject(**value)
                        for key, value in data.items()
                    }
                logger.info(f"Loaded state from {self.state_file} with {len(self._state)} objects")
            except Exception as e:
                logger.error(f"Error loading state from {self.state_file}: {e}")
                self._state = {}
        else:
            logger.info(f"No state file found at {self.state_file}, starting with empty state")
            self._state = {}

    def save(self) -> None:
        """Save state to JSON file."""
        try:
            # Convert ProcessedObject instances to dicts for JSON serialization
            data = {
                key: obj.model_dump()
                for key, obj in self._state.items()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving state to {self.state_file}: {e}")

    def get(self, object_key: str) -> Optional[ProcessedObject]:
        """
        Get state for an object.

        Args:
            object_key: R2 object key

        Returns:
            ProcessedObject if found, None otherwise
        """
        return self._state.get(object_key)

    def set(self, object_key: str, obj: ProcessedObject) -> None:
        """
        Set state for an object.

        Args:
            object_key: R2 object key
            obj: ProcessedObject to store
        """
        self._state[object_key] = obj
        self.save()
        logger.debug(f"Set state for object {object_key}")

    def delete(self, object_key: str) -> None:
        """
        Delete state for an object.

        Args:
            object_key: R2 object key
        """
        if object_key in self._state:
            del self._state[object_key]
            self.save()
            logger.debug(f"Deleted state for object {object_key}")

    def exists(self, object_key: str) -> bool:
        """
        Check if object has been processed.

        Args:
            object_key: R2 object key

        Returns:
            True if object exists in state, False otherwise
        """
        return object_key in self._state

    def clear(self) -> None:
        """Clear all state."""
        self._state = {}
        self.save()
        logger.info("Cleared all state")

    def count(self) -> int:
        """
        Get number of tracked objects.

        Returns:
            Number of objects in state
        """
        return len(self._state)