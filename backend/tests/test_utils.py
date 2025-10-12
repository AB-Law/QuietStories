"""
Unit tests for backend utilities.
"""

import pytest
import logging
from backend.utils.logger import get_logger, setup_logging


class TestLogger:
    """Test the logging utilities"""

    def test_get_logger(self):
        """Test that get_logger returns a logger instance"""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_setup_logging(self):
        """Test that setup_logging configures logging correctly"""
        # This is hard to test directly without side effects
        # Just test that it doesn't raise an exception
        try:
            setup_logging(level="INFO", enable_colors=False)
            assert True  # If we get here, it worked
        except Exception as e:
            pytest.fail(f"setup_logging raised an exception: {e}")

    def test_logger_levels(self):
        """Test that loggers respect log levels"""
        logger = get_logger("test_levels")

        # Set level to WARNING
        logger.setLevel(logging.WARNING)

        # This should not log anything (since it's DEBUG)
        logger.debug("This should not appear")

        # This should log (since it's WARNING)
        logger.warning("This should appear")

        assert logger.level == logging.WARNING