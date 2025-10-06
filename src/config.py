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
    model_provider: Literal["openai", "ollama", "generic"] = Field(
        default="openai", env="MODEL_PROVIDER"
    )
    openai_api_base: str = Field(
        default="https://api.openai.com/v1", env="OPENAI_API_BASE"
    )
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    model_name: str = Field(default="gpt-4", env="MODEL_NAME")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Monte Carlo Configuration
    monte_carlo_turns: int = Field(default=100, env="MONTE_CARLO_TURNS")
    negativity_min_fail_rate: float = Field(
        default=0.25, env="NEGATIVITY_MIN_FAIL_RATE"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
