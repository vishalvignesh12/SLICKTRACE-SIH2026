"""
Configuration module for R2 Ingestion Worker
Loads and manages environment variables for the worker.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for R2 Ingestion Worker."""

    # Cloudflare R2 Settings
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "slicktrace-sar-ingest")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL", "")
    R2_PUBLIC_BASE_URL: str = os.getenv("R2_PUBLIC_BASE_URL", "")
    R2_PREFIX: str = os.getenv("R2_PREFIX", "incoming/")

    # Backend API Settings
    INGESTION_API_URL: str = os.getenv("INGESTION_API_URL", "http://localhost:8000/api/v1/scenes/ingest")
    INGESTION_JWT: str = os.getenv("INGESTION_JWT", "")

    # Worker Settings
    R2_POLL_INTERVAL_SECONDS: int = int(os.getenv("R2_POLL_INTERVAL_SECONDS", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        required_fields = [
            "R2_ACCOUNT_ID",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_ENDPOINT_URL",
            "R2_PUBLIC_BASE_URL",
            "INGESTION_JWT"
        ]

        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")

        return True