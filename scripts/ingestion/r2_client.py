"""
Cloudflare R2 client wrapper
Provides S3-compatible interface for R2 operations.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional
from logger import setup_logger
from config import Config

logger = setup_logger(__name__)


class R2Client:
    """Wrapper for Cloudflare R2 (S3-compatible) operations.
    """

    def __init__(self):
        """Initialize R2 client with configuration."""
        self.config = Config()
        self.config.validate()

        self.client = boto3.client(
            's3',
            endpoint_url=self.config.R2_ENDPOINT_URL,
            aws_access_key_id=self.config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=self.config.R2_SECRET_ACCESS_KEY,
            region_name='us-east-1'  # Required but ignored by R2
        )
        logger.info(f"Initialized R2 client for bucket {self.config.R2_BUCKET_NAME}")

    def list_objects_with_prefix(self, prefix: str) -> List[Dict[str, Any]]:
        """
        List objects with given prefix.

        Args:
            prefix: Object key prefix to filter by

        Returns:
            List of object dictionaries with Key, ETag, Size, etc.
        """
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.R2_BUCKET_NAME,
                Prefix=prefix
            )

            objects = []
            for page in pages:
                if 'Contents' in page:
                    objects.extend(page['Contents'])

            logger.debug(f"Found {len(objects)} objects with prefix '{prefix}'")
            return objects
        except Exception as e:
            logger.error(f"Error listing objects with prefix '{prefix}': {e}")
            raise

    def object_exists(self, object_key: str) -> bool:
        """
        Check if an object exists.

        Args:
            object_key: R2 object key

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.client.head_object(
                Bucket=self.config.R2_BUCKET_NAME,
                Key=object_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking if object {object_key} exists: {e}")
            raise
        except Exception as e:
            logger.error(f"Error checking if object {object_key} exists: {e}")
            raise

    def get_object(self, object_key: str) -> bytes:
        """
        Get object content.

        Args:
            object_key: R2 object key

        Returns:
            Object content as bytes
        """
        try:
            response = self.client.get_object(
                Bucket=self.config.R2_BUCKET_NAME,
                Key=object_key
            )
            content = response['Body'].read()
            logger.debug(f"Retrieved object {object_key} ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Error getting object {object_key}: {e}")
            raise

    def get_object_etag(self, object_key: str) -> Optional[str]:
        """
        Get ETag of an object.

        Args:
            object_key: R2 object key

        Returns:
            ETag string if object exists, None otherwise
        """
        try:
            response = self.client.head_object(
                Bucket=self.config.R2_BUCKET_NAME,
                Key=object_key
            )
            etag = response.get('ETag', '').strip('"')
            logger.debug(f"ETag for {object_key}: {etag}")
            return etag
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Error getting ETag for {object_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting ETag for {object_key}: {e}")
            raise

    def get_public_url(self, object_key: str) -> str:
        """
        Get public URL for an object.

        Args:
            object_key: R2 object key

        Returns:
            Publicly accessible URL for the object
        """
        # Remove leading slash if present in prefix to avoid double slashes
        prefix = self.config.R2_PREFIX.lstrip('/')
        if prefix and not object_key.startswith(prefix):
            # If object_key doesn't start with prefix, assume it's relative to bucket root
            path = object_key
        else:
            path = object_key

        return f"{self.config.R2_PUBLIC_BASE_URL}/{path}"