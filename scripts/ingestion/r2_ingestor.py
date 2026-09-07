"""
Main R2 Ingestion Worker
Polls Cloudflare R2 for new Sentinel-1 SAR images and submits them to the ingestion API.
"""

import time
import threading
import os
from typing import Any, Dict, Optional
from config import Config
from logger import setup_logger
from r2_client import R2Client
from metadata import load_metadata_file, SceneMetadata
from api_client import APIClient
from state import StateManager
from models import ProcessedObject

logger = setup_logger(__name__)


class R2Ingestor:
    """Main worker for polling R2 and ingesting satellite scenes.
    """

    def __init__(self):
        """Initialize the R2 ingestor."""
        self.config = Config()
        self.config.validate()

        self.r2_client = R2Client()
        self.api_client = APIClient()
        self.state_manager = StateManager()

        # Supported image extensions
        self.image_extensions = {'.tif', '.tiff'}
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.storage_dir = os.path.join(project_root, "storage", "incoming")
        os.makedirs(self.storage_dir, exist_ok=True)
        logger.info(f"Local ML storage directory: {self.storage_dir}")
        logger.info("R2 Ingestor initialized")

    def _is_image_file(self, object_key: str) -> bool:
        """
        Check if an object is a supported image file.

        Args:
            object_key: R2 object key

        Returns:
            True if object is a supported image file, False otherwise
        """
        return any(object_key.lower().endswith(ext) for ext in self.image_extensions)

    def _get_metadata_key(self, image_key: str) -> str:
        """
        Get the metadata key for an image file.

        Args:
            image_key: R2 object key of image file

        Returns:
            R2 object key for corresponding metadata file
        """
        # Remove extension and add .json
        if image_key.lower().endswith('.tif'):
            return image_key[:-4] + '.json'
        elif image_key.lower().endswith('.tiff'):
            return image_key[:-5] + '.json'
        else:
            # Should not happen if _is_image_file is called first
            return image_key + '.json'

    def _download_image(self, object_key: str) -> str:
        filename = os.path.basename(object_key)
        local_path = os.path.join(self.storage_dir, filename)
        logger.info(f"Downloading {object_key} to {local_path}")
        image_content = self.r2_client.get_object(object_key)
        with open(local_path, "wb") as f:
            f.write(image_content)
        logger.info(
            f"Downloaded {object_key} successfully "
            f"({len(image_content)} bytes)"
        )

        return local_path

    def _process_image_object(self, image_object: Dict[str, Any]) -> None:
        """
        Process a single image object.

        Args:
            image_object: R2 object dictionary from list_objects_v2
        """
        object_key = image_object['Key']
        etag = image_object.get('ETag', '').strip('"')

        logger.info(f"Processing object: {object_key}")

        # Check if already processed
        existing_state = self.state_manager.get(object_key)
        if existing_state and existing_state.etag == etag:
            logger.info(f"Object {object_key} already processed with same ETag, skipping")
            return

        # Check if it's an image file
        if not self._is_image_file(object_key):
            logger.debug(f"Object {object_key} is not an image file, skipping")
            return

        # Get metadata key
        metadata_key = self._get_metadata_key(object_key)

        # Check if metadata exists
        if not self.r2_client.object_exists(metadata_key):
            logger.warning(f"No metadata file found for {object_key} (expected: {metadata_key}), skipping")
            # Mark as failed to avoid repeated attempts
            failed_state = ProcessedObject(
                object_key=object_key,
                etag=etag,
                scene_id="unknown",
                status="FAILED",
                error_message="Metadata file not found"
            )
            self.state_manager.set(object_key, failed_state)
            return

        try:
            # Load and validate metadata
            metadata_content = self.r2_client.get_object(metadata_key)
            metadata_str = metadata_content.decode('utf-8')
            metadata = load_metadata_file(object_key, metadata_str)

            # Download the TIFF locally as a development cache
            local_image_path = self._download_image(object_key)
            public_r2_url = self.r2_client.get_public_url(object_key)

            # Construct scene data for API submission - R2 is the source of truth
            scene_data = {
                "source": "cloudflare-r2-replay",
                "scene_id": metadata.scene_id,
                "satellite": metadata.satellite,
                "sensor": metadata.sensor,
                "product_type": metadata.product_type,
                "polarization": metadata.polarization,
                "acquisition_time": metadata.acquisition_time.isoformat(),
                "processing_time": metadata.processing_time.isoformat() if metadata.processing_time else None,
                "bbox": metadata.bbox,
                "image_url": public_r2_url or f"storage://incoming/{os.path.basename(local_image_path)}",
                "thumbnail_url": None,  # Could be derived from metadata if available
                "scene_metadata": metadata.scene_metadata or {},
                "status": "RECEIVED"
            }

            # Remove None values
            scene_data = {k: v for k, v in scene_data.items() if v is not None}

            # Submit to API
            api_response = self.api_client.ingest_scene(scene_data)

            # Update state with success
            success_state = ProcessedObject(
                object_key=object_key,
                etag=etag,
                scene_id=metadata.scene_id,
                analysis_id=api_response.get('analysis_id'),
                status="SUCCESS" if not api_response.get('is_duplicate') else "DUPLICATE",
                error_message=None
            )
            self.state_manager.set(object_key, success_state)

            if api_response.get('is_duplicate'):
                logger.info(f"Duplicate scene detected for {object_key} - {metadata.scene_id}")
            else:
                logger.info(f"Successfully ingested scene {metadata.scene_id} from {object_key}")

        except Exception as e:
            logger.error(f"Failed to process object {object_key}: {e}")
            # Mark as failed
            failed_state = ProcessedObject(
                object_key=object_key,
                etag=etag,
                scene_id="unknown",
                status="FAILED",
                error_message=str(e)
            )
            self.state_manager.set(object_key, failed_state)

    def run_once(self) -> None:
        """
        Run one polling cycle.
        """
        logger.info("Starting R2 polling cycle")

        try:
            # List objects in the incoming prefix
            objects = self.r2_client.list_objects_with_prefix(self.config.R2_PREFIX)
            logger.info(f"Found {len(objects)} objects in prefix '{self.config.R2_PREFIX}'")

            # Filter to image files
            image_objects = [obj for obj in objects if self._is_image_file(obj['Key'])]
            logger.info(f"Found {len(image_objects)} image objects")

            # Process each image object
            for image_obj in image_objects:
                self._process_image_object(image_obj)

        except Exception as e:
            logger.error(f"Error during polling cycle: {e}")

        logger.info("Completed R2 polling cycle")

    def run(self) -> None:
        """
        Run the ingestor continuously.
        """
        logger.info(f"Starting R2 Ingestor with poll interval {self.config.R2_POLL_INTERVAL_SECONDS}s")

        # Run once immediately on startup
        self.run_once()

        # Then run on interval
        while True:
            try:
                time.sleep(self.config.R2_POLL_INTERVAL_SECONDS)
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                # Continue running after unexpected error
                time.sleep(self.config.R2_POLL_INTERVAL_SECONDS)


def main() -> None:
    """Main entry point."""
    try:
        ingestor = R2Ingestor()
        ingestor.run()
    except Exception as e:
        logger.error(f"Failed to start R2 Ingestor: {e}")
        raise


if __name__ == "__main__":
    main()