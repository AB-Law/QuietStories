"""
Provider factory for creating LLM providers based on configuration
"""

from typing import Union

from ..config import DEFAULT_LMSTUDIO_API_BASE, settings
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
        # Use lmstudio_api_base if set, otherwise fall back to openai_api_base
        api_base = settings.lmstudio_api_base or settings.openai_api_base

        # If still using OpenAI default, switch to LM Studio default
        if api_base == "https://api.openai.com/v1":
            api_base = DEFAULT_LMSTUDIO_API_BASE

        return LMStudioProvider(
            api_base=api_base,
            api_key=settings.openai_api_key
            or "lm-studio",  # LMStudio doesn't require key
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
