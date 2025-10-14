"""
Embedding provider factory for semantic memory search.

This module provides a unified interface for different embedding providers,
allowing the system to use OpenAI, Ollama, or LM Studio embeddings based on configuration.
"""

from typing import Optional

from langchain.embeddings.base import Embeddings

from backend.config import DEFAULT_LMSTUDIO_API_BASE, settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def create_embedding_provider() -> Optional[Embeddings]:
    """
    Create an embedding provider based on configuration.

    The embedding provider is determined by:
    1. embedding_provider setting if explicitly set
    2. Falls back to model_provider if embedding_provider is None
    3. Returns None if provider is "none" or unavailable

    Returns:
        Embeddings instance or None if embeddings are disabled/unavailable
    """
    # Determine which provider to use
    provider = settings.embedding_provider or settings.model_provider

    if provider == "none":
        logger.info("Embedding provider explicitly disabled (set to 'none')")
        return None

    logger.info(f"Creating embedding provider: {provider}")

    try:
        if provider == "openai":
            return _create_openai_embeddings()
        elif provider == "ollama":
            return _create_ollama_embeddings()
        elif provider == "lmstudio":
            return _create_lmstudio_embeddings()
        elif provider == "generic":
            # Try to use as OpenAI-compatible
            logger.info("Using generic provider as OpenAI-compatible embeddings")
            return _create_openai_embeddings()
        else:
            logger.warning(f"Unknown embedding provider: {provider}")
            return None
    except Exception as e:
        logger.error(f"Failed to create embedding provider '{provider}': {e}")
        return None


def _create_openai_embeddings() -> Optional[Embeddings]:
    """Create OpenAI embedding provider"""
    try:
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr

        # Check for API key
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured, embeddings disabled")
            return None

        # Use embedding_api_base if set, otherwise fall back to openai_api_base
        api_base = settings.embedding_api_base or settings.openai_api_base

        embeddings = OpenAIEmbeddings(
            model=settings.embedding_model_name,
            api_key=SecretStr(settings.openai_api_key),
            base_url=api_base,
            chunk_size=1000,
        )

        logger.info(f"✓ Initialized OpenAI embeddings: {settings.embedding_model_name}")
        return embeddings
    except ImportError:
        logger.error(
            "langchain_openai not installed. Install with: pip install langchain-openai"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to create OpenAI embeddings: {e}")
        return None


def _create_ollama_embeddings() -> Optional[Embeddings]:
    """Create Ollama embedding provider"""
    try:
        from langchain_community.embeddings import OllamaEmbeddings

        # Use embedding_api_base if set, otherwise fall back to openai_api_base
        api_base = settings.embedding_api_base or settings.openai_api_base

        # Extract base URL without /v1 suffix for Ollama
        if api_base.endswith("/v1"):
            api_base = api_base[:-3]

        # Default model for Ollama if not specified
        model_name = settings.embedding_model_name
        if model_name == "text-embedding-3-small":  # OpenAI default
            model_name = "nomic-embed-text"  # Ollama default
            logger.info(f"Using Ollama default embedding model: {model_name}")

        embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=api_base,
        )

        logger.info(f"✓ Initialized Ollama embeddings: {model_name} at {api_base}")
        return embeddings
    except ImportError:
        logger.error(
            "langchain_community not installed. Install with: pip install langchain-community"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to create Ollama embeddings: {e}")
        return None


def _create_lmstudio_embeddings() -> Optional[Embeddings]:
    """
    Create LM Studio embedding provider.

    Uses custom LMStudioEmbeddings wrapper for better compatibility
    """
    try:
        from backend.providers.lmstudio_embeddings import LMStudioEmbeddings

        # Use embedding_api_base if set, otherwise lmstudio_api_base, then fall back to openai_api_base
        api_base = (
            settings.embedding_api_base
            or settings.lmstudio_api_base
            or settings.openai_api_base
        )

        # If still using OpenAI default, switch to LM Studio default
        if api_base == "https://api.openai.com/v1":
            api_base = DEFAULT_LMSTUDIO_API_BASE

        # Get model name from settings
        model_name = settings.embedding_model_name
        if model_name == "text-embedding-3-small":  # OpenAI default
            model_name = "text-embedding-nomic-embed-text-v1.5"  # LM Studio default
            logger.info(f"Using LM Studio default embedding model: {model_name}")

        embeddings = LMStudioEmbeddings(
            model=model_name,
            base_url=api_base,
        )

        logger.info(f"✓ Initialized LM Studio embeddings: {model_name} at {api_base}")
        return embeddings
    except ImportError as e:
        logger.error(f"Failed to import LMStudioEmbeddings: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to create LM Studio embeddings: {e}")
        return None


def test_embedding_provider(provider: Optional[Embeddings]) -> bool:
    """
    Test if an embedding provider is working.

    Args:
        provider: The embedding provider to test

    Returns:
        True if provider works, False otherwise
    """
    if provider is None:
        return False

    try:
        # Try to embed a simple test string
        test_text = "Hello, this is a test"
        embeddings = provider.embed_query(test_text)

        if embeddings and len(embeddings) > 0:
            logger.info(
                f"✓ Embedding provider test passed (dimension: {len(embeddings)})"
            )
            return True
        else:
            logger.warning("Embedding provider returned empty result")
            return False
    except Exception as e:
        logger.error(f"Embedding provider test failed: {e}")
        return False
