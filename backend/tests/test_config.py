"""
Unit tests for backend configuration.
"""

import pytest

from backend.config import Settings


class TestSettings:
    """Test the Settings configuration class"""

    def test_default_values(self):
        """Test that default values are set correctly"""
        settings = Settings()
        assert settings.model_provider in ["openai", "ollama", "generic"]
        assert isinstance(settings.model_name, str)
        assert isinstance(settings.database_path, str)
        assert isinstance(settings.debug, bool)
        assert isinstance(settings.monte_carlo_turns, int)
        assert settings.monte_carlo_turns > 0

    def test_environment_variables(self):
        """Test that environment variables override defaults"""
        import os

        original_env = os.environ.copy()

        try:
            os.environ["MODEL_NAME"] = "test-model"
            os.environ["DEBUG"] = "true"
            os.environ["MONTE_CARLO_TURNS"] = "50"

            settings = Settings()
            assert settings.model_name == "test-model"
            assert settings.debug is True
            assert settings.monte_carlo_turns == 50
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_database_path_construction(self):
        """Test that database path is constructed correctly"""
        settings = Settings()
        assert "quietstories.db" in settings.database_path
        assert settings.database_path.endswith("quietstories.db")
