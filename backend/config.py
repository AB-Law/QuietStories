"""
Configuration management for the Dynamic CYOA Engine
"""

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LLM Provider Configuration
    model_provider: Literal["openai", "ollama", "generic", "lmstudio"] = Field(default="openai")
    openai_api_base: str = Field(default="https://api.openai.com/v1")
    openai_api_key: str = Field(default="")
    model_name: str = Field(default="gpt-5-nano")

    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    # Verbose logging settings for debugging
    verbose_orchestrator: bool = True
    log_message_sequences: bool = True
    orchestrator_recursion_limit: int = Field(default=50)

    # Monte Carlo Configuration
    monte_carlo_turns: int = Field(default=100)
    negativity_min_fail_rate: float = Field(default=0.25)

    # Database Configuration
    database_path: str = Field(
        default="data/quietstories.db",
        description="SQLite database file path for storing scenarios and sessions",
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
