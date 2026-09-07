"""
Metadata validation for R2 Ingestion Worker
Validates sidecar metadata.json files for R2 objects.
"""
import json
from typing import Dict, Any
from datetime import datetime
from logger import setup_logger
from models import SceneMetadata

logger = setup_logger(__name__)


def validate_metadata_file(metadata_content: Dict[str, Any]) -> SceneMetadata:
    """
    Validate sidecar metadata content.

    Args:
        metadata_content: Parsed JSON from metadata.json file

    Returns:
        Validated SceneMetadata object

    Raises:
        ValueError: If metadata is invalid
    """
    try:
        # Pydantic will handle validation and type conversion
        metadata = SceneMetadata(**metadata_content)
        logger.debug(f"Validated metadata for scene {metadata.scene_id}")
        return metadata
    except Exception as e:
        logger.error(f"Metadata validation failed: {e}")
        raise ValueError(f"Invalid metadata: {e}")


def load_metadata_file(object_key: str, metadata_content: str) -> SceneMetadata:
    """
    Load and validate metadata from string content.

    Args:
        object_key: R2 object key (for logging)
        metadata_content: Raw JSON string from metadata.json

    Returns:
        Validated SceneMetadata object

    Raises:
        ValueError: If metadata is invalid or not valid JSON
    """
    try:
        metadata_dict = json.loads(metadata_content)
        return validate_metadata_file(metadata_dict)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metadata for object {object_key}: {e}")
        raise ValueError(f"Invalid JSON in metadata: {e}")
    except Exception as e:
        logger.error(f"Error loading metadata for object {object_key}: {e}")
        raise