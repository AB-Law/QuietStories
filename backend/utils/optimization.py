"""
LLM Call Optimization Utilities

This module provides optimization strategies for reducing token usage and
improving performance when working with LLMs, especially local models.

Key optimizations:
1. Context caching - Cache repeated system prompts
2. Memory summarization - Compress old memories
3. Smart context windowing - Only include relevant history
4. Token estimation - Track and limit token usage
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, cast

from langchain.schema import BaseMessage, HumanMessage, SystemMessage

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ContextCache:
    """
    Cache for frequently used context strings to reduce repeated token usage.

    Uses LRU-style eviction when cache grows too large.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize context cache.

        Args:
            max_size: Maximum number of cached items
        """
        self.cache: Dict[str, str] = {}
        self.access_count: Dict[str, int] = {}
        self.max_size = max_size

    def get(self, key: str) -> Optional[str]:
        """Get cached context by key."""
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            logger.debug(f"[Cache] Hit for key: {key[:50]}...")
            return self.cache[key]
        logger.debug(f"[Cache] Miss for key: {key[:50]}...")
        return None

    def set(self, key: str, value: str):
        """Set cached context."""
        # Evict least used item if cache is full
        if len(self.cache) >= self.max_size:
            least_used = min(self.access_count.items(), key=lambda x: x[1])[0]
            del self.cache[least_used]
            del self.access_count[least_used]
            logger.debug(f"[Cache] Evicted: {least_used[:50]}...")

        self.cache[key] = value
        self.access_count[key] = 0
        logger.debug(f"[Cache] Set key: {key[:50]}...")

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()
        self.access_count.clear()
        logger.info("[Cache] Cleared all items")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_accesses": sum(self.access_count.values()),
        }


# Global context cache instance
_context_cache = ContextCache(max_size=50)


def get_context_cache() -> ContextCache:
    """Get the global context cache instance."""
    return _context_cache


class TokenEstimator:
    """
    Estimate token usage for prompt optimization.

    Uses a simple character-based estimation for speed.
    For more accuracy, could integrate tiktoken or similar.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.

        Uses rough approximation: ~4 characters per token for English text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // 4

    @staticmethod
    def estimate_messages_tokens(messages: List[BaseMessage]) -> int:
        """
        Estimate total tokens in a message list.

        Args:
            messages: List of LangChain messages

        Returns:
            Estimated total token count
        """
        total = 0
        for msg in messages:
            content = msg.content if hasattr(msg, "content") else str(msg)
            if isinstance(content, str):
                total += TokenEstimator.estimate_tokens(content)
            elif isinstance(content, list):
                # Handle list content (mixed media)
                for item in content:
                    if isinstance(item, str):
                        total += TokenEstimator.estimate_tokens(item)
                    elif isinstance(item, dict):
                        total += TokenEstimator.estimate_tokens(json.dumps(item))

        # Add overhead for message formatting (role, etc.)
        total += len(messages) * 4

        return total


class MemorySummarizer:
    """
    Summarize and compress memory entries to reduce token usage.

    Strategies:
    1. Remove redundant information
    2. Merge similar memories
    3. Keep only important/recent memories
    """

    @staticmethod
    def summarize_memories(
        memories: List[Dict[str, Any]],
        max_memories: int = 10,
        importance_threshold: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Summarize memory list by filtering and prioritizing.

        Args:
            memories: List of memory entries
            max_memories: Maximum memories to keep
            importance_threshold: Minimum importance to keep (1-10)

        Returns:
            Filtered and prioritized memory list
        """
        if not memories:
            return []

        # Filter by importance
        important_memories = [
            m for m in memories if m.get("importance", 5) >= importance_threshold
        ]

        # Sort by importance and recency (turn)
        sorted_memories = sorted(
            important_memories,
            key=lambda m: (m.get("importance", 5), m.get("turn", 0)),
            reverse=True,
        )

        # Take top N
        result = sorted_memories[:max_memories]

        if len(memories) > len(result):
            logger.debug(
                f"[Summarizer] Reduced memories from {len(memories)} to {len(result)}"
            )

        return result

    @staticmethod
    def compress_memory_content(content: str, max_length: int = 200) -> str:
        """
        Compress memory content to reduce token usage.

        Args:
            content: Memory content string
            max_length: Maximum character length

        Returns:
            Compressed content string
        """
        if len(content) <= max_length:
            return content

        # Simple truncation with ellipsis
        # Could be improved with extractive summarization
        return content[: max_length - 3] + "..."


class ContextOptimizer:
    """
    Optimize context sent to LLM by reducing redundancy and token usage.

    Strategies:
    1. Smart turn history windowing
    2. Memory summarization
    3. Redundant information removal
    4. Context caching
    """

    def __init__(
        self,
        max_turn_history: int = 10,
        max_memories_per_entity: int = 10,
        max_context_tokens: int = 4000,
        enable_caching: bool = True,
    ):
        """
        Initialize context optimizer.

        Args:
            max_turn_history: Maximum turns to include in history
            max_memories_per_entity: Maximum memories per entity
            max_context_tokens: Target maximum context size in tokens
            enable_caching: Whether to enable context caching
        """
        self.max_turn_history = max_turn_history
        self.max_memories_per_entity = max_memories_per_entity
        self.max_context_tokens = max_context_tokens
        self.enable_caching = enable_caching
        self.cache = get_context_cache()
        self.token_estimator = TokenEstimator()

    def optimize_messages(
        self, messages: List[BaseMessage], preserve_system: bool = True
    ) -> List[BaseMessage]:
        """
        Optimize message list to reduce token usage.

        Args:
            messages: Original message list
            preserve_system: Always keep system messages

        Returns:
            Optimized message list
        """
        if not messages:
            return messages

        # Estimate current token usage
        current_tokens = self.token_estimator.estimate_messages_tokens(messages)
        logger.debug(f"[Optimizer] Current estimated tokens: {current_tokens}")

        if current_tokens <= self.max_context_tokens:
            return messages

        logger.info(
            f"[Optimizer] Context too large ({current_tokens} tokens), optimizing..."
        )

        # Separate system and non-system messages
        system_messages = []
        other_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage) and preserve_system:
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # Apply sliding window to conversation history
        # Keep most recent messages that fit in budget
        system_messages_typed = cast(List[BaseMessage], system_messages)
        system_tokens = self.token_estimator.estimate_messages_tokens(
            system_messages_typed
        )
        remaining_budget = self.max_context_tokens - system_tokens

        optimized_others: List[BaseMessage] = []
        current_budget = 0

        # Add messages from most recent to oldest
        for msg in reversed(other_messages):
            msg_tokens = self.token_estimator.estimate_messages_tokens([msg])
            if current_budget + msg_tokens <= remaining_budget:
                optimized_others.insert(0, msg)
                current_budget += msg_tokens
            else:
                break

        result = system_messages + optimized_others
        new_tokens = self.token_estimator.estimate_messages_tokens(result)

        logger.info(
            f"[Optimizer] Reduced from {len(messages)} to {len(result)} messages "
            f"({current_tokens} -> {new_tokens} tokens)"
        )

        return result

    def optimize_turn_history(
        self, turn_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Optimize turn history by keeping only recent relevant turns.

        Args:
            turn_history: Full turn history

        Returns:
            Optimized turn history
        """
        if len(turn_history) <= self.max_turn_history:
            return turn_history

        # Keep most recent turns
        optimized = turn_history[-self.max_turn_history :]

        logger.debug(
            f"[Optimizer] Turn history: {len(turn_history)} -> {len(optimized)} turns"
        )

        return optimized

    def optimize_entity_memories(
        self,
        private_memory: Dict[str, List[Dict[str, Any]]],
        public_memory: Dict[str, List[Dict[str, Any]]],
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        """
        Optimize entity memories by summarizing and filtering.

        Args:
            private_memory: Private memories by entity
            public_memory: Public memories by entity

        Returns:
            Tuple of (optimized_private, optimized_public)
        """
        summarizer = MemorySummarizer()

        optimized_private = {}
        optimized_public = {}

        # Optimize private memories
        for entity_id, memories in private_memory.items():
            optimized_private[entity_id] = summarizer.summarize_memories(
                memories, max_memories=self.max_memories_per_entity
            )

        # Optimize public memories
        for entity_id, memories in public_memory.items():
            optimized_public[entity_id] = summarizer.summarize_memories(
                memories, max_memories=self.max_memories_per_entity
            )

        logger.debug(
            f"[Optimizer] Optimized memories for {len(private_memory)} entities"
        )

        return optimized_private, optimized_public

    def build_context_string(
        self,
        game_state: Dict[str, Any],
        entities: List[Dict[str, Any]],
        turn_history: Optional[List[Dict[str, Any]]] = None,
        private_memory: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        public_memory: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> str:
        """
        Build optimized context string from game state.

        Args:
            game_state: Current game state
            entities: Entity list
            turn_history: Turn history (optional)
            private_memory: Private memories (optional)
            public_memory: Public memories (optional)

        Returns:
            Optimized context string
        """
        # Create cache key from game state hash
        state_hash = hashlib.md5(
            json.dumps(game_state, sort_keys=True).encode()
        ).hexdigest()[:16]

        cache_key = f"context_{state_hash}"

        # Check cache if enabled
        if self.enable_caching:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        # Build context parts
        context_parts = []

        # Game state (always included)
        context_parts.append(f"=== GAME STATE ===\n{json.dumps(game_state, indent=2)}")

        # Entities (summarized)
        if entities:
            entity_summary = self._summarize_entities(entities)
            context_parts.append(f"=== ENTITIES ===\n{entity_summary}")

        # Turn history (windowed)
        if turn_history:
            optimized_history = self.optimize_turn_history(turn_history)
            history_summary = self._summarize_turn_history(optimized_history)
            context_parts.append(f"=== RECENT HISTORY ===\n{history_summary}")

        # Memories (summarized)
        if private_memory or public_memory:
            opt_private, opt_public = self.optimize_entity_memories(
                private_memory or {}, public_memory or {}
            )
            memory_summary = self._summarize_memories(opt_private, opt_public)
            if memory_summary:
                context_parts.append(f"=== MEMORIES ===\n{memory_summary}")

        # Combine all parts
        context_string = "\n\n".join(context_parts)

        # Cache result if enabled
        if self.enable_caching:
            self.cache.set(cache_key, context_string)

        return context_string

    def _summarize_entities(self, entities: List[Dict[str, Any]]) -> str:
        """Summarize entity list for context."""
        summaries = []
        for entity in entities[:10]:  # Limit to first 10
            name = entity.get("name", entity.get("id", "Unknown"))
            entity_type = entity.get("type", "Unknown")
            background = entity.get("background", "")

            # Truncate long backgrounds
            if background and len(background) > 150:
                background = background[:147] + "..."

            summary = f"- {name} ({entity_type})"
            if background:
                summary += f": {background}"

            summaries.append(summary)

        if len(entities) > 10:
            summaries.append(f"... and {len(entities) - 10} more entities")

        return "\n".join(summaries)

    def _summarize_turn_history(self, turn_history: List[Dict[str, Any]]) -> str:
        """Summarize turn history for context."""
        summaries = []
        for turn in turn_history:
            turn_num = turn.get("turn", "?")
            action = turn.get("user_action", "")
            narrative = turn.get("narrative", "")

            # Truncate long narratives
            if narrative and len(narrative) > 200:
                narrative = narrative[:197] + "..."

            summary = f"Turn {turn_num}: {action}\n  → {narrative}"
            summaries.append(summary)

        return "\n\n".join(summaries)

    def _summarize_memories(
        self,
        private_memory: Dict[str, List[Dict[str, Any]]],
        public_memory: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Summarize memories for context."""
        summaries = []

        # Combine all memories
        all_entities = set(list(private_memory.keys()) + list(public_memory.keys()))

        for entity_id in list(all_entities)[:5]:  # Limit to 5 entities
            entity_summaries = []

            # Private memories
            if entity_id in private_memory:
                for mem in private_memory[entity_id][:3]:  # Max 3 per entity
                    content = mem.get("content", "")
                    if len(content) > 100:
                        content = content[:97] + "..."
                    entity_summaries.append(f"  [Private] {content}")

            # Public memories
            if entity_id in public_memory:
                for mem in public_memory[entity_id][:3]:  # Max 3 per entity
                    content = mem.get("content", "")
                    if len(content) > 100:
                        content = content[:97] + "..."
                    entity_summaries.append(f"  [Public] {content}")

            if entity_summaries:
                summaries.append(f"{entity_id}:\n" + "\n".join(entity_summaries))

        return "\n\n".join(summaries)


# Global optimizer instance
_global_optimizer = ContextOptimizer(
    max_turn_history=10,
    max_memories_per_entity=10,
    max_context_tokens=4000,
    enable_caching=True,
)


def get_optimizer() -> ContextOptimizer:
    """Get the global context optimizer instance."""
    return _global_optimizer


def configure_optimizer(
    max_turn_history: Optional[int] = None,
    max_memories_per_entity: Optional[int] = None,
    max_context_tokens: Optional[int] = None,
    enable_caching: Optional[bool] = None,
):
    """
    Configure the global optimizer settings.

    Args:
        max_turn_history: Maximum turns in history
        max_memories_per_entity: Maximum memories per entity
        max_context_tokens: Maximum context size in tokens
        enable_caching: Whether to enable caching
    """
    global _global_optimizer

    if max_turn_history is not None:
        _global_optimizer.max_turn_history = max_turn_history
    if max_memories_per_entity is not None:
        _global_optimizer.max_memories_per_entity = max_memories_per_entity
    if max_context_tokens is not None:
        _global_optimizer.max_context_tokens = max_context_tokens
    if enable_caching is not None:
        _global_optimizer.enable_caching = enable_caching

    logger.info(f"[Optimizer] Configuration updated")
