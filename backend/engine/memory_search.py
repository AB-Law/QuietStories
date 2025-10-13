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

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SemanticMemorySearch:
    """
    Semantic memory search using vector embeddings.

    This class provides intelligent memory retrieval based on semantic similarity
    rather than exact text matching, allowing the LLM to find relevant memories
    even when the query doesn't use exact keywords.
    """

    def __init__(self, persist_directory: str = "data/chroma_memories"):
        """
        Initialize the semantic memory search system.

        Args:
            persist_directory: Directory to persist the vector database
        """
        self.persist_directory = persist_directory
        self.embedding_model = None
        self.collection = None

        if not CHROMA_AVAILABLE:
            logger.warning("ChromaDB not available. Install with: pip install chromadb")
            return

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning(
                "Sentence transformers not available. Install with: pip install sentence-transformers"
            )
            return

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Initialized semantic memory search with sentence transformers")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            return

        # Initialize ChromaDB
        try:
            os.makedirs(persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=persist_directory, settings=Settings(anonymized_telemetry=False)
            )

            # Create or get collection for memories
            self.collection = self.client.get_or_create_collection(
                name="entity_memories",
                metadata={"description": "Semantic search for entity memories"},
            )
            logger.info(f"Initialized ChromaDB collection in {persist_directory}")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")

    def is_available(self) -> bool:
        """Check if semantic search is available"""
        return (
            CHROMA_AVAILABLE
            and SENTENCE_TRANSFORMERS_AVAILABLE
            and self.embedding_model is not None
            and self.collection is not None
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
            logger.warning("Semantic search not available, skipping memory indexing")
            return False

        try:
            # Generate embedding for the memory content
            if self.embedding_model is None:
                return False
            embedding = self.embedding_model.encode(content).tolist()

            # Prepare metadata
            metadata_dict = {"memory_id": memory_id, "content": content, **metadata}

            # Add to ChromaDB
            if self.collection is None:
                return False
            self.collection.add(
                ids=[memory_id], embeddings=[embedding], metadatas=[metadata_dict]
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
            logger.warning("Semantic search not available, returning empty results")
            return []

        try:
            # Generate embedding for the query
            if self.embedding_model is None:
                return []
            query_embedding = self.embedding_model.encode(query).tolist()

            # Prepare where clause for filtering
            where_clause = {}
            if entity_id:
                where_clause["entity_id"] = entity_id
            if scope:
                where_clause["scope"] = scope

            # Search in ChromaDB
            if self.collection is None:
                return []
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit * 2,  # Get more to filter by threshold
                where=where_clause if where_clause else None,
            )

            # Process results
            memories = []
            if results["distances"] and results["distances"][0]:
                for i, distance in enumerate(results["distances"][0]):
                    # Convert distance to similarity (ChromaDB uses cosine distance)
                    similarity = 1.0 - distance

                    if similarity >= threshold:
                        metadata = results["metadatas"][0][i]
                        memories.append(
                            {
                                "memory_id": metadata["memory_id"],
                                "content": metadata["content"],
                                "similarity": similarity,
                                "metadata": metadata,
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
            # Delete old embedding
            if self.collection is not None:
                self.collection.delete(ids=[memory_id])

            # Add new embedding
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
            if self.collection is not None:
                self.collection.delete(ids=[memory_id])
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
            count = 0
            if self.collection is not None:
                count = self.collection.count()
            return {
                "available": True,
                "total_memories": count,
                "embedding_model": "all-MiniLM-L6-v2" if self.embedding_model else None,
                "persist_directory": self.persist_directory,
            }
        except Exception as e:
            logger.error(f"Failed to get semantic search stats: {e}")
            return {"available": False, "error": str(e)}
