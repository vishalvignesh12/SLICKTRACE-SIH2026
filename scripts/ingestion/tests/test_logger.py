"""
Unit tests for logger.py
"""
import logging
from logger import setup_logger


def test_setup_logger_returns_logger():
    """Test that setup_logger returns a logging.Logger instance."""
    logger = setup_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_setup_logger_sets_level():
    """Test that setup_logger sets the logging level."""
    logger = setup_logger("test_logger", "DEBUG")
    assert logger.level == logging.DEBUG

    logger2 = setup_logger("test_logger2", "INFO")
    assert logger2.level == logging.INFO


def test_setup_logger_adds_handler():
    """Test that setup_logger adds a handler if none exists."""
    logger = setup_logger("test_logger_handler_test")
    # Clear any existing handlers for a clean test
    logger.handlers.clear()

    logger = setup_logger("test_logger_handler_test")
    assert len(logger.handlers) >= 1

    # Should be a StreamHandler
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


def test_setup_logger_formatter():
    """Test that setup_logger sets up a formatter."""
    logger = setup_logger("test_logger_formatter_test")
    # Clear handlers for clean test
    logger.handlers.clear()
    logger = setup_logger("test_logger_formatter_test")

    assert len(logger.handlers) >= 1
    handler = logger.handlers[0]
    assert handler.formatter is not None

    # Check that it's the expected format
    fmt = handler.formatter._fmt
    assert "%(asctime)s" in fmt
    assert "%(name)s" in fmt
    assert "%(levelname)s" in fmt
    assert "%(message)s" in fmt