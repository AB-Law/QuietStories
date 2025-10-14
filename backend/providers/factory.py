"""
Provider factory for creating LLM providers based on configuration
"""

from typing import Union

from ..config import settings
from .base import BaseProvider
from .generic import GenericProvider
from .lmstudio import LMStudioProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider


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
    elif settings.model_provider == "lmstudio":
        # LMStudio uses default localhost endpoint if not specified
        api_base = settings.openai_api_base
        if api_base == "https://api.openai.com/v1":
            api_base = "http://localhost:5101/v1"
        
        return LMStudioProvider(
            api_base=api_base,
            api_key=settings.openai_api_key or "lm-studio",  # LMStudio doesn't require key
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
