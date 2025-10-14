"""
Semantic memory search using vector embeddings for intelligent memory retrieval.

This module provides semantic search capabilities for memories using vector embeddings,
allowing the LLM to query memories by meaning rather than exact text matching.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

try:
    import chromadb
    from chromadb.config import Settings
    from langchain_chroma import Chroma
    from langchain_community.vectorstores.utils import filter_complex_metadata
    from langchain_openai import OpenAIEmbeddings

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SemanticMemorySearch:
    """
    Semantic memory search using vector embeddings.

    This class provides intelligent memory retrieval based on semantic similarity
    rather than exact text matching, allowing the LLM to find relevant memories
    even when the query doesn't use exact keywords.
    """

    def __init__(
        self, session_id: str, persist_directory: str = "data/chroma_memories"
    ):
        """
        Initialize the semantic memory search system.

        Args:
            session_id: Unique session identifier for collection isolation
            persist_directory: Directory to persist the vector database
        """
        self.session_id = session_id
        self.persist_directory = persist_directory
        self.collection_name = f"session_{session_id}"
        self.embedding_model = None
        self.vectorstore = None

        if not CHROMA_AVAILABLE:
            logger.warning(
                "ChromaDB not available. Install with: pip install chromadb langchain-chroma"
            )
            return

        # Check if OpenAI API key is available
        if not settings.openai_api_key:
            logger.info(
                "OpenAI API key not configured. Semantic memory search will be disabled. "
                "Add OPENAI_API_KEY to environment variables to enable semantic search."
            )
            return

        # Initialize embedding model
        try:
            from pydantic import SecretStr

            if settings.openai_api_base:
                self.embedding_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    chunk_size=1000,
                    api_key=(
                        SecretStr(settings.openai_api_key)
                        if settings.openai_api_key
                        else None
                    ),
                    base_url=settings.openai_api_base,
                )
            else:
                self.embedding_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    chunk_size=1000,
                    api_key=(
                        SecretStr(settings.openai_api_key)
                        if settings.openai_api_key
                        else None
                    ),
                )
            logger.info("Initialized semantic memory search with OpenAI embeddings")
        except Exception as e:
            logger.info(
                f"Could not initialize embedding model: {e}. Semantic search disabled."
            )
            return

        # Initialize ChromaDB with LangChain
        try:
            os.makedirs(persist_directory, exist_ok=True)
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_model,
                persist_directory=persist_directory,
            )
            logger.info(
                f"Initialized ChromaDB collection '{self.collection_name}' in {persist_directory}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")

    def is_available(self) -> bool:
        """Check if semantic search is available"""
        return (
            CHROMA_AVAILABLE
            and self.embedding_model is not None
            and self.vectorstore is not None
        )

    def add_memory(
        self, memory_id: str, content: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Add a memory to the semantic search index.

        Args:
            memory_id: Unique identifier for the memory
            content: The memory content text
            metadata: Additional metadata (entity_id, scope, turn, etc.)

        Returns:
            True if successfully added, False otherwise
        """
        if not self.is_available():
            logger.debug("Semantic search not available, skipping memory indexing")
            return False

        try:
            # Prepare metadata and filter complex types
            metadata_dict = {"memory_id": memory_id, **metadata}

            # Filter out complex metadata types (lists, dicts, etc.) that ChromaDB can't handle
            filtered_metadata = {}
            for key, value in metadata_dict.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    filtered_metadata[key] = value
                elif isinstance(value, (list, dict)):
                    # Convert complex types to strings
                    filtered_metadata[key] = str(value)
                else:
                    filtered_metadata[key] = str(value)

            # Add to vectorstore
            if self.vectorstore is None:
                return False

            self.vectorstore.add_texts(
                texts=[content], ids=[memory_id], metadatas=[filtered_metadata]
            )

            logger.debug(f"Added memory {memory_id} to semantic index")
            return True

        except Exception as e:
            logger.error(f"Failed to add memory to semantic index: {e}")
            return False

    def search_memories(
        self,
        query: str,
        entity_id: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Search for memories by semantic similarity.

        Args:
            query: The search query
            entity_id: Filter by specific entity (optional)
            scope: Filter by memory scope (optional)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of matching memories with similarity scores
        """
        if not self.is_available():
            logger.debug("Semantic search not available, returning empty results")
            return []

        try:
            # Prepare filters
            filters = {}
            if entity_id:
                filters["entity_id"] = entity_id
            if scope:
                filters["scope"] = scope

            # Search in vectorstore
            if self.vectorstore is None:
                return []

            search_results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=limit * 2,  # Get more to filter by threshold
                filter=filters if filters else None,
            )

            # Process results
            memories = []
            for doc, score in search_results:
                # Convert score to similarity (higher is better)
                similarity = 1.0 - score if score <= 1.0 else 1.0 / (1.0 + score)

                if similarity >= threshold:
                    memories.append(
                        {
                            "memory_id": doc.metadata.get("memory_id", "unknown"),
                            "content": doc.page_content,
                            "similarity": similarity,
                            "metadata": doc.metadata,
                        }
                    )

            # Sort by similarity and limit
            memories.sort(key=lambda x: x["similarity"], reverse=True)
            memories = memories[:limit]

            logger.debug(
                f"Found {len(memories)} semantically similar memories for query: {query}"
            )
            return memories

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def update_memory(
        self, memory_id: str, content: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Update an existing memory in the semantic index.

        Args:
            memory_id: The memory ID to update
            content: New content
            metadata: Updated metadata

        Returns:
            True if successfully updated, False otherwise
        """
        if not self.is_available():
            return False

        try:
            # Delete old embedding and add new one
            self.delete_memory(memory_id)
            return self.add_memory(memory_id, content, metadata)

        except Exception as e:
            logger.error(f"Failed to update memory in semantic index: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from the semantic index.

        Args:
            memory_id: The memory ID to delete

        Returns:
            True if successfully deleted, False otherwise
        """
        if not self.is_available():
            return False

        try:
            if self.vectorstore is not None:
                self.vectorstore.delete(ids=[memory_id])
            logger.debug(f"Deleted memory {memory_id} from semantic index")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory from semantic index: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the semantic memory index"""
        if not self.is_available():
            return {"available": False}

        try:
            # Try to get collection stats through the underlying client
            count = 0
            if self.vectorstore is not None:
                try:
                    # Access the underlying Chroma collection for stats
                    collection = self.vectorstore._collection
                    count = collection.count() if collection else 0
                except:
                    count = 0

            return {
                "available": True,
                "total_memories": count,
                "embedding_model": (
                    "text-embedding-3-small" if self.embedding_model else None
                ),
                "persist_directory": self.persist_directory,
                "collection_name": self.collection_name,
                "session_id": self.session_id,
            }
        except Exception as e:
            logger.error(f"Failed to get semantic search stats: {e}")
            return {"available": False, "error": str(e)}
