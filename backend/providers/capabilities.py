"""
Provider capabilities matrix and model family detection.

Defines capabilities for different LLM model families and provides
automatic routing based on model name prefixes.
"""

from enum import Enum
from typing import Dict, Literal, Optional

from pydantic import BaseModel


class APIFamily(str, Enum):
    """API family types for different model generations."""

    RESPONSES = "responses"  # GPT-5 models using Responses API
    CHAT_COMPLETIONS = "chat_completions"  # GPT-4o and earlier using Chat Completions
    OPENAI_COMPATIBLE = "openai_compatible"  # LM Studio, Ollama, etc.


class ModelCapabilities(BaseModel):
    """Capabilities for a model family."""

    api_family: APIFamily
    supports_temperature: bool = True
    supports_tools: bool = True
    supports_structured_output: bool = True
    supports_streaming: bool = True
    default_max_tokens: int = 4096
    requires_special_json_parsing: bool = False


# Model family capability definitions
MODEL_CAPABILITIES: Dict[str, ModelCapabilities] = {
    # GPT-5 family - uses Responses API
    "gpt-5": ModelCapabilities(
        api_family=APIFamily.RESPONSES,
        supports_temperature=False,  # Only supports default temperature (1.0)
        supports_tools=True,
        supports_structured_output=True,
        supports_streaming=True,
        default_max_tokens=4096,
        requires_special_json_parsing=True,  # Requires robust JSON extraction
    ),
    # GPT-4o family - uses Chat Completions
    "gpt-4o": ModelCapabilities(
        api_family=APIFamily.CHAT_COMPLETIONS,
        supports_temperature=True,
        supports_tools=True,
        supports_structured_output=True,
        supports_streaming=True,
        default_max_tokens=4096,
        requires_special_json_parsing=False,
    ),
    # GPT-4 family - uses Chat Completions
    "gpt-4": ModelCapabilities(
        api_family=APIFamily.CHAT_COMPLETIONS,
        supports_temperature=True,
        supports_tools=True,
        supports_structured_output=True,
        supports_streaming=True,
        default_max_tokens=4096,
        requires_special_json_parsing=False,
    ),
    # GPT-3.5 family - uses Chat Completions
    "gpt-3.5": ModelCapabilities(
        api_family=APIFamily.CHAT_COMPLETIONS,
        supports_temperature=True,
        supports_tools=True,
        supports_structured_output=True,
        supports_streaming=True,
        default_max_tokens=4096,
        requires_special_json_parsing=False,
    ),
}


def detect_model_family(model_name: str) -> str:
    """
    Detect the model family from model name.

    Args:
        model_name: Full model name (e.g., "gpt-5-nano", "gpt-4o-mini")

    Returns:
        Model family prefix (e.g., "gpt-5", "gpt-4o")
    """
    # Check for known prefixes
    for prefix in MODEL_CAPABILITIES.keys():
        if model_name.startswith(prefix):
            return prefix

    # Default to gpt-4 for unknown OpenAI models
    if model_name.startswith("gpt-"):
        return "gpt-4"

    # For non-OpenAI models, return a special marker
    return "openai-compatible"


def get_model_capabilities(model_name: str) -> ModelCapabilities:
    """
    Get capabilities for a model.

    Args:
        model_name: Full model name (e.g., "gpt-5-nano", "gpt-4o-mini")

    Returns:
        ModelCapabilities for the model family
    """
    family = detect_model_family(model_name)

    # Return capabilities for the detected family
    if family in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[family]

    # Default to OpenAI-compatible for unknown models
    return ModelCapabilities(
        api_family=APIFamily.OPENAI_COMPATIBLE,
        supports_temperature=True,
        supports_tools=False,  # Conservative default
        supports_structured_output=False,  # Conservative default
        supports_streaming=True,
        default_max_tokens=2048,
        requires_special_json_parsing=True,  # Use robust parsing for unknown models
    )


def is_gpt5_model(model_name: str) -> bool:
    """
    Check if a model is a GPT-5 family model.

    Args:
        model_name: Full model name

    Returns:
        True if model is GPT-5 family
    """
    return model_name.startswith("gpt-5")


def is_gpt4o_model(model_name: str) -> bool:
    """
    Check if a model is a GPT-4o family model.

    Args:
        model_name: Full model name

    Returns:
        True if model is GPT-4o family
    """
    return model_name.startswith("gpt-4o")


def get_api_family(model_name: str) -> APIFamily:
    """
    Get the API family for a model.

    Args:
        model_name: Full model name

    Returns:
        APIFamily enum value
    """
    capabilities = get_model_capabilities(model_name)
    return capabilities.api_family
