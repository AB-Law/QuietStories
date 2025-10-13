"""
Caching utilities for performance optimization.

This module provides various caching mechanisms to improve response times
and reduce computational overhead in the QuietStories application.
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple
from functools import lru_cache

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ResponseCache:
    """
    Simple in-memory response cache with TTL support.

    This cache stores LLM responses and other expensive computations
    to avoid redundant processing.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize the response cache.

        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        # Create a normalized representation of the arguments
        key_data = {
            'args': args,
            'kwargs': kwargs
        }

        # Convert to JSON string for consistent hashing
        key_str = json.dumps(key_data, sort_keys=True)

        # Generate hash
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, *args, **kwargs) -> Optional[Any]:
        """
        Retrieve item from cache if it exists and hasn't expired.

        Returns:
            Cached item or None if not found/expired
        """
        key = self._make_key(*args, **kwargs)
        now = time.time()

        if key in self.cache:
            value, expiry = self.cache[key]

            if now < expiry:
                self.hits += 1
                logger.debug(f"Cache hit for key: {key[:8]}...")
                return value
            else:
                # Expired, remove from cache
                del self.cache[key]
                self.misses += 1
                logger.debug(f"Cache expired for key: {key[:8]}...")
        else:
            self.misses += 1

        return None

    def set(self, value: Any, *args, ttl: Optional[int] = None, **kwargs) -> None:
        """
        Store item in cache with optional TTL.

        Args:
            value: Item to cache
            ttl: Time-to-live in seconds (uses default if None)
            *args, **kwargs: Arguments to generate cache key
        """
        key = self._make_key(*args, **kwargs)
        expiry = time.time() + (ttl or self.default_ttl)

        # Implement simple LRU by removing oldest items if at max size
        if len(self.cache) >= self.max_size:
            # Remove oldest items (simple implementation)
            oldest_keys = sorted(self.cache.keys(),
                               key=lambda k: self.cache[k][1])[:len(self.cache) // 4]
            for old_key in oldest_keys:
                del self.cache[old_key]

        self.cache[key] = (value, expiry)
        logger.debug(f"Cached item with key: {key[:8]}... (TTL: {ttl or self.default_ttl}s)")

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Response cache cleared")

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }


class MemoryCache:
    """
    Specialized cache for memory-related operations.

    This cache stores frequently accessed memory summaries and
    entity data to reduce database queries.
    """

    def __init__(self):
        self.entity_summaries: Dict[str, Tuple[str, float]] = {}
        self.relationship_data: Dict[str, Tuple[Dict, float]] = {}
        self.emotional_states: Dict[str, Tuple[Dict, float]] = {}

    def get_entity_summary(self, entity_id: str) -> Optional[str]:
        """Get cached entity summary."""
        if entity_id in self.entity_summaries:
            summary, expiry = self.entity_summaries[entity_id]
            if time.time() < expiry:
                return summary
            else:
                del self.entity_summaries[entity_id]
        return None

    def set_entity_summary(self, entity_id: str, summary: str, ttl: int = 300) -> None:
        """Cache entity summary."""
        self.entity_summaries[entity_id] = (summary, time.time() + ttl)

    def get_relationships(self, session_id: str) -> Optional[Dict]:
        """Get cached relationship data."""
        if session_id in self.relationship_data:
            data, expiry = self.relationship_data[session_id]
            if time.time() < expiry:
                return data
            else:
                del self.relationship_data[session_id]
        return None

    def set_relationships(self, session_id: str, data: Dict, ttl: int = 180) -> None:
        """Cache relationship data."""
        self.relationship_data[session_id] = (data, time.time() + ttl)

    def get_emotional_states(self, session_id: str) -> Optional[Dict]:
        """Get cached emotional state data."""
        if session_id in self.emotional_states:
            data, expiry = self.emotional_states[session_id]
            if time.time() < expiry:
                return data
            else:
                del self.emotional_states[session_id]
        return None

    def set_emotional_states(self, session_id: str, data: Dict, ttl: int = 120) -> None:
        """Cache emotional state data."""
        self.emotional_states[session_id] = (data, time.time() + ttl)

    def clear_session(self, session_id: str) -> None:
        """Clear all cached data for a specific session."""
        keys_to_remove = [
            k for k in self.entity_summaries.keys()
            if k.startswith(f"{session_id}:")
        ]

        for key in keys_to_remove:
            del self.entity_summaries[key]

        # Remove session-specific caches
        if session_id in self.relationship_data:
            del self.relationship_data[session_id]
        if session_id in self.emotional_states:
            del self.emotional_states[session_id]

        logger.debug(f"Cleared cache for session: {session_id}")

    def stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        return {
            'entity_summaries': len(self.entity_summaries),
            'relationship_data': len(self.relationship_data),
            'emotional_states': len(self.emotional_states)
        }


# Global cache instances
response_cache = ResponseCache()
memory_cache = MemoryCache()


@lru_cache(maxsize=128)
def cached_prompt_enrichment(description: str, max_tokens: int = 500) -> str:
    """
    Cached version of prompt enrichment.

    This decorator caches the results of expensive prompt enrichment
    operations to avoid redundant LLM calls.
    """
    # This would normally call the actual enrichment function
    # For now, just return a placeholder
    return f"Enriched: {description[:100]}... (cached)"


def cache_prompt_result(func):
    """
    Decorator to cache LLM prompt results.

    This decorator can be applied to any function that processes
    prompts to cache the results and avoid redundant processing.
    """
    def wrapper(*args, **kwargs):
        # Try to get from cache first
        cached_result = response_cache.get(*args, **kwargs)
        if cached_result is not None:
            return cached_result

        # Execute the function
        result = func(*args, **kwargs)

        # Cache the result
        response_cache.set(result, *args, **kwargs)

        return result

    return wrapper


def invalidate_session_cache(session_id: str) -> None:
    """
    Invalidate all cached data for a session.

    This should be called when a session is modified to ensure
    cached data doesn't become stale.
    """
    memory_cache.clear_session(session_id)
    logger.debug(f"Invalidated cache for session: {session_id}")


def get_cache_statistics() -> Dict[str, Any]:
    """Get comprehensive cache statistics."""
    return {
        'response_cache': response_cache.stats(),
        'memory_cache': memory_cache.stats()
    }
