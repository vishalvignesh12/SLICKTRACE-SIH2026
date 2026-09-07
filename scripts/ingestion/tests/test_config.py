"""
Unit tests for config.py
"""
import os
from unittest.mock import patch
from config import Config


def test_config_loads_from_environment():
    """Test that Config loads values from environment variables."""
    test_env = {
        "R2_ACCOUNT_ID": "test-account",
        "R2_ACCESS_KEY_ID": "test-access-key",
        "R2_SECRET_ACCESS_KEY": "test-secret-key",
        "R2_ENDPOINT_URL": "https://test.r2.cloudflarestorage.com",
        "R2_PUBLIC_BASE_URL": "https://test.example.com",
        "INGESTION_JWT": "test-jwt-token",
        "R2_POLL_INTERVAL_SECONDS": "60",
        "MAX_RETRIES": "3",
        "REQUEST_TIMEOUT_SECONDS": "15",
        "LOG_LEVEL": "DEBUG"
    }

    with patch.dict(os.environ, test_env, clear=False):
        # Reload the module to pick up new environment variables
        import importlib
        import sys
        if 'config' in sys.modules:
            importlib.reload(sys.modules['config'])
        # Re-import to get the reloaded module
        from config import Config as ReloadedConfig

        assert ReloadedConfig.R2_ACCOUNT_ID == "test-account"
        assert ReloadedConfig.R2_ACCESS_KEY_ID == "test-access-key"
        assert ReloadedConfig.R2_SECRET_ACCESS_KEY == "test-secret-key"
        assert ReloadedConfig.R2_ENDPOINT_URL == "https://test.r2.cloudflarestorage.com"
        assert ReloadedConfig.R2_PUBLIC_BASE_URL == "https://test.example.com"
        assert ReloadedConfig.INGESTION_JWT == "test-jwt-token"
        assert ReloadedConfig.R2_POLL_INTERVAL_SECONDS == 60
        assert ReloadedConfig.MAX_RETRIES == 3
        assert ReloadedConfig.REQUEST_TIMEOUT_SECONDS == 15
        assert ReloadedConfig.LOG_LEVEL == "DEBUG"


def test_config_has_defaults():
    """Test that Config provides default values."""
    # These should be the defaults from the class definition
    assert Config.R2_BUCKET_NAME == "slicktrace-sar-ingest"
    assert Config.R2_PREFIX == "incoming/"
    assert Config.INGESTION_API_URL == "http://localhost:8000/api/v1/scenes"


def test_config_validate_raises_on_missing_fields():
    """Test that validate() raises ValueError for missing required fields."""
    required_fields = [
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_ENDPOINT_URL",
        "R2_PUBLIC_BASE_URL",
        "INGESTION_JWT"
    ]

    with patch.dict(
        os.environ,
        {field: "" for field in required_fields},
        clear=False
    ):
        import importlib
        import sys

        importlib.reload(sys.modules["config"])
        from config import Config as ReloadedConfig

        config = ReloadedConfig()

        try:
            config.validate()
            assert False, "Expected ValueError to be raised"
        except ValueError as e:
            assert "Missing required environment variables" in str(e)