"""
Provider factory for creating LLM providers based on configuration
"""

from typing import Union
from .base import BaseProvider
from .openai import OpenAIProvider
from .ollama import OllamaProvider
from .generic import GenericProvider
from ..config import settings


def create_provider() -> BaseProvider:
    """Create a provider instance based on configuration"""
    
    if settings.model_provider == "openai":
        return OpenAIProvider(
            api_base=settings.openai_api_base,
            api_key=settings.openai_api_key,
            model_name=settings.model_name,
        )
    elif settings.model_provider == "ollama":
        return OllamaProvider(
            api_base=settings.openai_api_base,  # Use same config for Ollama
            api_key=settings.openai_api_key,
            model_name=settings.model_name,
        )
    elif settings.model_provider == "generic":
        return GenericProvider(
            api_base=settings.openai_api_base,
            api_key=settings.openai_api_key,
            model_name=settings.model_name,
        )
    else:
        raise ValueError(f"Unsupported provider: {settings.model_provider}")
