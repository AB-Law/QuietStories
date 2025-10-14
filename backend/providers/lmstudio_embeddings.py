"""
Custom LM Studio embeddings provider that ensures compatibility.

LM Studio's embeddings API requires specific formatting that may differ
from the standard OpenAI format. This wrapper ensures requests are formatted correctly.
"""

from typing import List

import requests  # type: ignore
from langchain.embeddings.base import Embeddings

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class LMStudioEmbeddings(Embeddings):
    """
    Custom embeddings provider for LM Studio.

    This directly calls the LM Studio API to ensure proper formatting,
    avoiding potential issues with LangChain's OpenAIEmbeddings wrapper.
    """

    def __init__(
        self,
        model: str = "text-embedding-nomic-embed-text-v1.5",
        base_url: str = "http://localhost:1234/v1",
    ):
        """
        Initialize LM Studio embeddings provider.

        Args:
            model: Name of the embedding model loaded in LM Studio
            base_url: Base URL for LM Studio API
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.embeddings_url = f"{self.base_url}/embeddings"

        logger.info(
            f"Initialized LMStudioEmbeddings: model='{model}', url='{self.embeddings_url}'"
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            # LM Studio accepts array of strings in 'input' field
            response = requests.post(
                self.embeddings_url,
                json={"model": self.model, "input": texts},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Extract embeddings from response
            # Response format: {"data": [{"embedding": [...], "index": 0}, ...]}
            embeddings = []
            for item in sorted(data["data"], key=lambda x: x["index"]):
                embeddings.append(item["embedding"])

            logger.debug(
                f"Generated {len(embeddings)} embeddings for {len(texts)} texts"
            )
            return embeddings

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Return empty embeddings on error to avoid breaking the flow
            return [[0.0] * 768 for _ in texts]  # nomic-embed-text has 768 dimensions

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        try:
            # LM Studio accepts string or array of strings
            # Using string for single query
            response = requests.post(
                self.embeddings_url,
                json={"model": self.model, "input": text},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Extract first embedding
            embedding = data["data"][0]["embedding"]

            logger.debug(f"Generated embedding for query (dimension: {len(embedding)})")
            return embedding

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate query embedding: {e}")
            # Return empty embedding on error
            return [0.0] * 768  # nomic-embed-text has 768 dimensions
