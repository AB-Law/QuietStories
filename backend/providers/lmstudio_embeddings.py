"""
Custom LMStudio embeddings wrapper for direct API calls.

This wrapper handles LM Studio's embeddings API directly to avoid
compatibility issues with LangChain's OpenAI embeddings implementation.
"""

import logging
from typing import List

import requests  # type: ignore
from langchain.embeddings.base import Embeddings

from backend.config import DEFAULT_LMSTUDIO_API_BASE, settings


class LMStudioEmbeddings(Embeddings):
    """Custom embeddings provider for LM Studio API"""

    def __init__(
        self,
        api_base: str = DEFAULT_LMSTUDIO_API_BASE,
        model_name: str = "local-embedding-model",
    ):
        """
        Initialize LMStudio embeddings.

        Args:
            api_base: LMStudio server URL (default: http://localhost:1234/v1)
            model_name: Name of the embedding model
        """
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.

        Args:
            texts: List of text documents to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        for text in texts:
            embedding = self.embed_query(text)
            embeddings.append(embedding)

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            self.logger.debug(f"Embedding text (length: {len(text)})")

            response = requests.post(
                f"{self.api_base}/embeddings",
                json={
                    "input": text,
                    "model": self.model_name,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Error handling for malformed API responses
            if "data" not in data:
                raise ValueError(f"API response missing 'data' key: {data}")

            if not data["data"]:
                raise ValueError(f"API response 'data' array is empty: {data}")

            if not isinstance(data["data"], list):
                raise ValueError(f"API response 'data' is not a list: {data}")

            item = data["data"][0]
            if "embedding" not in item:
                raise ValueError(f"API response item missing 'embedding' key: {item}")

            embedding = item["embedding"]
            if not isinstance(embedding, list):
                raise ValueError(f"Embedding is not a list: {embedding}")

            if not embedding:
                raise ValueError(f"Embedding list is empty: {embedding}")

            self.logger.debug(
                f"Successfully embedded text (dimension: {len(embedding)})"
            )
            return embedding

        except requests.RequestException as e:
            self.logger.exception(f"Request failed: {e}")
            raise
        except (KeyError, IndexError, ValueError) as e:
            self.logger.exception(f"API response parsing failed: {e}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error in embedding: {e}")
            raise
