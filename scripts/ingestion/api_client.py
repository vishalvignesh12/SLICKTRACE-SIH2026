"""
API client for communicating with the oil spill detection backend
Handles authentication and communication with the ingestion API.
"""

import requests
from typing import Dict, Any, Optional
from logger import setup_logger
from config import Config

logger = setup_logger(__name__)


class APIClient:
    """Client for interacting with the oil spill detection backend API.
    """

    def __init__(self):
        """Initialize API client with configuration."""
        self.config = Config()
        self.config.validate()

        self.base_url = self.config.INGESTION_API_URL.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {self.config.INGESTION_JWT}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        logger.info(f"Initialized API client for {self.base_url}")

    def ingest_scene(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit scene metadata to the ingestion API.

        Args:
            scene_data: Scene metadata conforming to SceneCreate schema

        Returns:
            API response dictionary

        Raises:
            requests.exceptions.RequestException: For HTTP errors
        """
        url = f"{self.base_url}/ingest"

        try:
            logger.debug(f"Submitting scene to {url}: {scene_data.get('scene_id', 'unknown')}")
            response = requests.post(
                url,
                json=scene_data,
                headers=self.headers,
                timeout=self.config.REQUEST_TIMEOUT_SECONDS
            )

            # Log response details
            logger.debug(f"API response status: {response.status_code}")

            # Handle different response types
            if response.status_code == 202:
                # Success - scene queued for processing
                result = response.json()
                logger.info(f"Scene ingested successfully: {result.get('scene_id')} "
                           f"(analysis_id: {result.get('analysis_id')}, "
                           f"is_duplicate: {result.get('is_duplicate')})")
                return result
            elif response.status_code == 401:
                logger.error("Authentication failed - invalid or missing JWT")
                raise requests.exceptions.HTTPError("Authentication failed", response=response)
            elif response.status_code == 403:
                logger.error("Forbidden - insufficient permissions (requires analyst role)")
                raise requests.exceptions.HTTPError("Forbidden - insufficient permissions", response=response)
            elif response.status_code == 422:
                # Validation error - don't retry
                error_detail = response.json().get('detail', 'Validation failed')
                logger.error(f"Validation error: {error_detail}")
                raise requests.exceptions.HTTPError(f"Validation error: {error_detail}", response=response)
            else:
                # Other HTTP errors
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                response.raise_for_status()
                return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to {url} failed: {e}")
            raise

    def health_check(self) -> bool:
        """
        Check if the API is healthy.

        Returns:
            True if API is responsive, False otherwise
        """
        try:
            # Try to hit the scenes list endpoint (should be lightweight)
            url = f"{self.base_url.replace('/scenes/ingest', '/scenes')}"
            response = requests.get(
                url,
                headers=self.headers,
                timeout=5  # Short timeout for health check
            )
            return response.status_code == 200
        except Exception:
            return False