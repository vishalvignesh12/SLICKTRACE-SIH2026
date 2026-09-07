"""
Logging configuration for R2 Ingestion Worker
Provides consistent logging across all modules.
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (defaults to INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set level if provided (override any existing level)
    if level is not None:
        logger.setLevel(getattr(logging, level.upper()))
    # Only set default level if not already configured (avoid overriding)
    elif not logger.handlers:
        logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in logger.handlers):
        # Create console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger