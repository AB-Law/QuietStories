"""
Configuration management for QuietStories.
"""

from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_LMSTUDIO_PORT = 1234
DEFAULT_LMSTUDIO_API_BASE = f"http://localhost:{DEFAULT_LMSTUDIO_PORT}/v1"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider
    model_provider: Literal["openai", "ollama", "generic", "lmstudio"] = Field(
        default="openai"
    )
    openai_api_base: str = Field(default="https://api.openai.com/v1")
    openai_api_key: str = Field(default="")
    model_name: str = Field(default="gpt-4o-mini")

    lmstudio_api_base: Optional[str] = Field(
        default=None,
        description=f"LM Studio API base URL. Defaults to {DEFAULT_LMSTUDIO_API_BASE}",
    )

    # Database
    database_path: str = Field(
        default="data/quietstories.db",
        description="SQLite database file path",
    )

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)

    # CORS
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Memory system
    memory_summary_interval: int = Field(
        default=15,
        description="Run the memory summarizer every N turns, updating actor known_facts",
    )
    memory_retrieval_recent: int = Field(
        default=5,
        description="Always include this many recent memories per active actor",
    )
    memory_retrieval_tagged: int = Field(
        default=10,
        description="Max tag-matched memories to retrieve per actor per turn",
    )

    # NPC engine
    npc_offscene_interval: int = Field(
        default=2,
        description="Off-scene NPCs act every N turns (catching up on N turns of activity)",
    )

    # Logging
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default=None)
    enable_console_logs: bool = Field(default=True)

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
