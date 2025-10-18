"""
Unit tests for backend utilities.
"""

import logging

import pytest

from backend.utils.logger import VERBOSE, get_logger, setup_logging


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

    def test_verbose_level(self):
        """Test that VERBOSE level is properly configured"""
        # VERBOSE should be between DEBUG and INFO
        assert VERBOSE > logging.DEBUG
        assert VERBOSE < logging.INFO
        assert VERBOSE == 15

    def test_verbose_logging(self):
        """Test that verbose logging method works"""
        logger = get_logger("test_verbose")
        logger.setLevel(VERBOSE)

        # Test that logger has verbose method
        assert hasattr(logger, "verbose")

        # This should not raise an exception
        try:
            logger.verbose("This is a verbose message")  # type: ignore
            assert True
        except Exception as e:
            pytest.fail(f"verbose logging raised an exception: {e}")

    def test_setup_logging_with_verbose(self):
        """Test that setup_logging works with VERBOSE level"""
        try:
            setup_logging(
                level="VERBOSE", enable_colors=False, enable_file_logging=False
            )
            logger = get_logger("test_verbose_setup")
            # Verify the logger is set to VERBOSE level
            assert logger.level <= VERBOSE or logging.getLogger().level <= VERBOSE
            assert True
        except Exception as e:
            pytest.fail(f"setup_logging with VERBOSE raised an exception: {e}")
