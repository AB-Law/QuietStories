"""
Enhanced memory management for scoped entity memory types
"""

from collections import defaultdict
from typing import Any, Dict, List, Literal, Optional

from backend.engine.memory_search import SemanticMemorySearch
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Define valid memory scopes
MemoryScope = Literal["belief", "relationship", "event", "location", "goal", "general", "emotion"]

# Define valid memory visibility levels
MemoryVisibility = Literal["private", "public"]


class MemoryManager:
    """Enhanced memory manager with scoped memory types for entities"""

    def __init__(
        self,
        session_id: str,
        db_manager=None,
        initial_private_memory=None,
        initial_public_memory=None,
        initial_turn_count=0,
    ):
        self.session_id = session_id
        self.db_manager = db_manager
        self.turn_count = initial_turn_count

        # Enhanced memory storage with scopes
        # Structure: {entity_id: {scope: {visibility: [memories]}}}
        self.scoped_memory: Dict[
            str, Dict[str, Dict[str, List[Dict[str, Any]]]]
        ] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))  # type: ignore
        )

        # Legacy compatibility - flatten scoped memories for existing API
        self.private_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.public_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Load initial memory if provided
        if initial_private_memory:
            for entity_id, memories in initial_private_memory.items():
                self.private_memory[entity_id] = memories
        if initial_public_memory:
            for entity_id, memories in initial_public_memory.items():
                self.public_memory[entity_id] = memories

        # Convert legacy format to scoped format if needed
        self._convert_legacy_memories()

        # Initialize semantic search
        self.semantic_search = SemanticMemorySearch()

    def get_private_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get private memory for an entity (legacy compatibility)"""
        return self.private_memory.get(entity_id, [])

    def get_public_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all public memory (legacy compatibility)"""
        return dict(self.public_memory)

    def update_scoped_memory(
        self,
        entity_id: str,
        scope: MemoryScope,
        content: str,
        visibility: MemoryVisibility = "private",
        related_entities: Optional[List[str]] = None,
        importance: int = 5,
    ):
        """Update scoped memory for an entity"""
        memory_entry = {
            "content": content,
            "scope": scope,
            "visibility": visibility,
            "turn": self.turn_count,
            "importance": importance,
            "related_entities": related_entities or [],
        }

        self.scoped_memory[entity_id][scope][visibility].append(memory_entry)

        # Add to semantic search index
        memory_id = f"{entity_id}_{scope}_{self.turn_count}_{len(self.scoped_memory[entity_id][scope][visibility])}"
        metadata = {
            "entity_id": entity_id,
            "scope": scope,
            "visibility": visibility,
            "turn": self.turn_count,
            "importance": importance,
            "related_entities": related_entities or [],
        }

        if self.semantic_search.is_available():
            self.semantic_search.add_memory(memory_id, content, metadata)

        # Update legacy format for backward compatibility
        if visibility == "private":
            self.private_memory[entity_id].append(
                {"content": content, "scope": scope, "turn": self.turn_count}
            )
        else:
            self.public_memory[entity_id].append(
                {"content": content, "turn": self.turn_count}
            )

    def get_scoped_memory(
        self,
        entity_id: str,
        scope: Optional[MemoryScope] = None,
        visibility: Optional[MemoryVisibility] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get scoped memory for an entity"""
        if entity_id not in self.scoped_memory:
            return []

        memories = []
        entity_scopes = self.scoped_memory[entity_id]

        # Get memories from all scopes or specific scope
        if scope:
            scopes_to_check: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
                scope: entity_scopes.get(scope, {})
            }
        else:
            scopes_to_check = entity_scopes

        for scope_name, visibilities in scopes_to_check.items():
            for visibility_name, memory_list in visibilities.items():
                # Filter by visibility if specified
                if visibility and visibility_name != visibility:
                    continue

                # Sort by importance and turn, take most recent/important
                sorted_memories = sorted(
                    memory_list,
                    key=lambda m: (m["importance"], m["turn"]),
                    reverse=True,
                )
                memories.extend(sorted_memories[:limit])

        return memories

    def query_relationship_memory(
        self, entity_a: str, entity_b: str
    ) -> List[Dict[str, Any]]:
        """Query relationship-specific memories between two entities"""
        relationship_memories = []

        for entity_id in [entity_a, entity_b]:
            if entity_id in self.scoped_memory:
                for scope_data in self.scoped_memory[entity_id].values():
                    for visibility_data in scope_data.values():
                        for memory in visibility_data:
                            if memory["scope"] == "relationship":
                                related_entities = memory.get("related_entities", [])
                                if (
                                    entity_a in related_entities
                                    or entity_b in related_entities
                                ):
                                    relationship_memories.append(memory)

        # Sort by turn (most recent first)
        return sorted(relationship_memories, key=lambda m: m["turn"], reverse=True)

    def get_relationship_summary(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Get a summary of all character relationships with sentiment scores"""
        relationships = {}

        for entity_id in self.scoped_memory:
            # Look for relationship memories involving this entity
            entity_relationships = []

            for scope_data in self.scoped_memory[entity_id].values():
                for visibility_data in scope_data.values():
                    for memory in visibility_data:
                        if memory["scope"] == "relationship":
                            related_entities = memory.get("related_entities", [])
                            for related_entity in related_entities:
                                if related_entity != entity_id:
                                    # Calculate sentiment based on memory content
                                    sentiment_score = self._analyze_relationship_sentiment(
                                        memory["content"]
                                    )

                                    entity_relationships.append({
                                        "entity_a": entity_id,
                                        "entity_b": related_entity,
                                        "sentiment": sentiment_score,
                                        "memory_count": 1,
                                        "last_interaction": memory["turn"],
                                        "relationship_type": self._classify_relationship_type(
                                            memory["content"]
                                        )
                                    })

            # Group and summarize relationships
            for rel in entity_relationships:
                key = tuple(sorted([rel["entity_a"], rel["entity_b"]]))
                if key not in relationships:
                    relationships[key] = rel.copy()
                else:
                    # Update with most recent data
                    existing = relationships[key]
                    existing["sentiment"] = (existing["sentiment"] + rel["sentiment"]) / 2
                    existing["memory_count"] += 1
                    existing["last_interaction"] = max(existing["last_interaction"], rel["last_interaction"])

        return relationships

    def _analyze_relationship_sentiment(self, content: str) -> float:
        """Analyze sentiment of relationship memory content"""
        content_lower = content.lower()

        # Positive indicators
        positive_words = ["love", "friend", "trust", "respect", "care", "help", "support", "loyal", "close", "bond"]
        negative_words = ["hate", "enemy", "distrust", "betray", "anger", "fear", "avoid", "conflict", "tension"]

        positive_score = sum(1 for word in positive_words if word in content_lower)
        negative_score = sum(1 for word in negative_words if word in content_lower)

        # Normalize to -1 to 1 scale
        total_indicators = positive_score + negative_score
        if total_indicators == 0:
            return 0.0  # Neutral

        return (positive_score - negative_score) / total_indicators

    def _classify_relationship_type(self, content: str) -> str:
        """Classify the type of relationship based on memory content"""
        content_lower = content.lower()

        if any(word in content_lower for word in ["family", "sibling", "parent", "child", "blood"]):
            return "family"
        elif any(word in content_lower for word in ["friend", "companion", "ally", "trust"]):
            return "friendship"
        elif any(word in content_lower for word in ["romantic", "love", "partner", "spouse"]):
            return "romantic"
        elif any(word in content_lower for word in ["enemy", "rival", "opponent", "foe"]):
            return "adversarial"
        elif any(word in content_lower for word in ["mentor", "teacher", "student", "guide"]):
            return "mentor"
        elif any(word in content_lower for word in ["boss", "employee", "subordinate", "leader"]):
            return "professional"
        else:
            return "acquaintance"

    def update_emotional_state(
        self,
        entity_id: str,
        emotion: str,
        intensity: float,
        cause: Optional[str] = None,
        target_entity: Optional[str] = None,
    ):
        """Update emotional state for an entity"""
        # Validate emotion
        valid_emotions = ["joy", "sadness", "anger", "fear", "disgust", "surprise", "trust", "anticipation"]
        if emotion not in valid_emotions:
            logger.warning(f"Invalid emotion: {emotion}. Using 'neutral' instead.")
            emotion = "neutral"

        # Clamp intensity to valid range
        intensity = max(-1.0, min(1.0, intensity))

        emotional_entry = {
            "emotion": emotion,
            "intensity": intensity,
            "cause": cause,
            "target_entity": target_entity,
            "turn": self.turn_count,
            "timestamp": None,  # Could be set by caller if needed
        }

        # Store in scoped memory under "emotion" scope
        self.scoped_memory[entity_id]["emotion"]["private"].append(emotional_entry)

        # Update legacy format for backward compatibility
        emotion_summary = f"Feeling {emotion} (intensity: {intensity:.2f})"
        if cause:
            emotion_summary += f" because {cause}"
        if target_entity:
            emotion_summary += f" towards {target_entity}"

        self.private_memory[entity_id].append({
            "content": emotion_summary,
            "scope": "emotion",
            "turn": self.turn_count
        })

        logger.debug(f"Updated emotional state for {entity_id}: {emotion} ({intensity:.2f})")

    def get_emotional_state(self, entity_id: str, recent_turns: int = 10) -> Dict[str, Any]:
        """Get current emotional state for an entity"""
        if entity_id not in self.scoped_memory:
            return {"dominant_emotion": "neutral", "intensity": 0.0, "recent_emotions": []}

        emotion_memories = self.get_scoped_memory(entity_id, scope="emotion", limit=recent_turns)

        if not emotion_memories:
            return {"dominant_emotion": "neutral", "intensity": 0.0, "recent_emotions": []}

        # Calculate dominant emotion and average intensity
        emotion_counts = {}
        total_intensity = 0.0

        for memory in emotion_memories:
            emotion = memory.get("emotion", "neutral")
            intensity = memory.get("intensity", 0.0)

            if emotion not in emotion_counts:
                emotion_counts[emotion] = {"count": 0, "total_intensity": 0.0}

            emotion_counts[emotion]["count"] += 1
            emotion_counts[emotion]["total_intensity"] += intensity
            total_intensity += abs(intensity)

        if not emotion_counts:
            return {"dominant_emotion": "neutral", "intensity": 0.0, "recent_emotions": []}

        # Find dominant emotion (most frequent and intense)
        dominant_emotion = "neutral"
        max_score = 0

        for emotion, data in emotion_counts.items():
            # Score combines frequency and intensity
            avg_intensity = data["total_intensity"] / data["count"]
            score = data["count"] * (1 + abs(avg_intensity))
            if score > max_score:
                max_score = score
                dominant_emotion = emotion

        avg_intensity = emotion_counts[dominant_emotion]["total_intensity"] / emotion_counts[dominant_emotion]["count"]

        return {
            "dominant_emotion": dominant_emotion,
            "intensity": avg_intensity,
            "recent_emotions": emotion_memories[:5],  # Last 5 emotional states
            "emotion_distribution": emotion_counts
        }

    def get_emotional_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get emotional state summary for all entities"""
        summary = {}

        for entity_id in self.scoped_memory:
            summary[entity_id] = self.get_emotional_state(entity_id)

        return summary

    def consolidate_memories(self, max_memories_per_entity: int = 50, consolidation_threshold: int = 10) -> Dict[str, Any]:
        """
        Consolidate memories by summarizing and merging similar memories.

        This helps prevent memory bloat by:
        1. Merging duplicate or very similar memories
        2. Summarizing old memories into higher-level concepts
        3. Removing low-importance memories when count exceeds threshold

        Args:
            max_memories_per_entity: Maximum memories to keep per entity per scope
            consolidation_threshold: Minimum memories before consolidation kicks in

        Returns:
            Summary of consolidation actions taken
        """
        consolidation_summary = {
            "entities_processed": 0,
            "memories_removed": 0,
            "memories_merged": 0,
            "memories_summarized": 0,
            "entities_consolidated": []
        }

        for entity_id in self.scoped_memory:
            entity_consolidated = False

            for scope in self.scoped_memory[entity_id]:
                for visibility in self.scoped_memory[entity_id][scope]:
                    memories = self.scoped_memory[entity_id][scope][visibility]

                    if len(memories) > consolidation_threshold:
                        # Filter and sort memories by importance and turn
                        valid_memories = [m for m in memories if isinstance(m, dict)]
                        if len(valid_memories) > consolidation_threshold:
                            # Sort by importance and turn (most recent/important first)
                            sorted_memories = sorted(
                                valid_memories,
                                key=lambda m: (m.get("importance", 5), m.get("turn", 0)),
                                reverse=True
                            )

                            # Keep only the most important memories
                            kept_memories = sorted_memories[:max_memories_per_entity]
                            removed_count = len(valid_memories) - len(kept_memories)

                            if removed_count > 0:
                                # Replace with consolidated memories
                                self.scoped_memory[entity_id][scope][visibility] = kept_memories
                                consolidation_summary["memories_removed"] += removed_count
                                entity_consolidated = True

                                # Update legacy format as well
                                if visibility == "private":
                                    self.private_memory[entity_id] = [
                                        {"content": m["content"], "scope": m["scope"], "turn": m["turn"]}
                                        for m in kept_memories if m.get("scope") != "emotion"  # Skip emotion memories for legacy compatibility
                                    ]
                                else:
                                    self.public_memory[entity_id] = [
                                        {"content": m["content"], "turn": m["turn"]}
                                        for m in kept_memories
                                    ]

            if entity_consolidated:
                consolidation_summary["entities_processed"] += 1
                consolidation_summary["entities_consolidated"].append(entity_id)

        logger.info(f"Memory consolidation completed: {consolidation_summary}")
        return consolidation_summary

    def summarize_entity_memories(self, entity_id: str, scope: Optional[str] = None) -> str:
        """
        Generate a summary of an entity's memories for context building.

        Args:
            entity_id: Entity to summarize
            scope: Optional scope to limit summary to

        Returns:
            Human-readable summary of the entity's memories
        """
        if entity_id not in self.scoped_memory:
            return f"No memories found for {entity_id}"

        summary_parts = []

        # Get memories for all scopes or specific scope
        if scope:
            scopes_to_check = {scope: self.scoped_memory[entity_id].get(scope, {})}
        else:
            scopes_to_check = self.scoped_memory[entity_id]

        for scope_name, visibilities in scopes_to_check.items():
            scope_memories = []

            for visibility_name, memory_list in visibilities.items():
                # Sort by importance and turn
                sorted_memories = sorted(
                    memory_list,
                    key=lambda m: (m["importance"], m["turn"]),
                    reverse=True
                )
                scope_memories.extend(sorted_memories[:5])  # Top 5 memories per scope

            if scope_memories:
                # Group memories by type for better summary
                memory_texts = [m["content"] for m in scope_memories]

                if memory_texts:
                    summary_text = f"{scope_name.title()}: {'; '.join(memory_texts)}"
                    summary_parts.append(summary_text)

        return " | ".join(summary_parts) if summary_parts else f"No significant memories in {scope or 'any scope'} for {entity_id}"

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current memory state.

        Returns:
            Dictionary with memory statistics
        """
        stats = {
            "total_entities": len(self.scoped_memory),
            "total_memories": 0,
            "memory_distribution": {},
            "oldest_memory_turn": float('inf'),
            "newest_memory_turn": 0,
            "average_importance": 0.0
        }

        all_importances = []

        for entity_id, scopes in self.scoped_memory.items():
            entity_memory_count = 0

            for scope_name, visibilities in scopes.items():
                for visibility_name, memories in visibilities.items():
                    count = len(memories)
                    entity_memory_count += count
                    stats["total_memories"] += count

                    if scope_name not in stats["memory_distribution"]:
                        stats["memory_distribution"][scope_name] = 0
                    stats["memory_distribution"][scope_name] += count

                    # Track turn ranges and importances
                    for memory in memories:
                        if isinstance(memory, dict):
                            turn = memory.get("turn", 0)
                            stats["oldest_memory_turn"] = min(stats["oldest_memory_turn"], turn)
                            stats["newest_memory_turn"] = max(stats["newest_memory_turn"], turn)
                            all_importances.append(memory.get("importance", 5))

            if entity_memory_count > 0:
                # Track entities with most memories
                if "largest_entities" not in stats:
                    stats["largest_entities"] = []
                stats["largest_entities"].append({
                    "entity_id": entity_id,
                    "memory_count": entity_memory_count
                })

        # Sort largest entities
        if "largest_entities" in stats:
            stats["largest_entities"].sort(key=lambda x: x["memory_count"], reverse=True)
            stats["largest_entities"] = stats["largest_entities"][:10]  # Top 10

        # Calculate average importance
        if all_importances:
            stats["average_importance"] = sum(all_importances) / len(all_importances)

        # Handle case where no memories exist
        if stats["total_memories"] == 0:
            stats["oldest_memory_turn"] = 0
            stats["newest_memory_turn"] = 0

        return stats

    def get_belief_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get belief-related memories for an entity"""
        return self.get_scoped_memory(entity_id, scope="belief")

    def get_goal_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get goal-related memories for an entity"""
        return self.get_scoped_memory(entity_id, scope="goal")

    def get_event_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get event-related memories for an entity"""
        return self.get_scoped_memory(entity_id, scope="event")

    def get_location_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get location-related memories for an entity"""
        return self.get_scoped_memory(entity_id, scope="location")

    def search_memories_semantic(
        self,
        query: str,
        entity_id: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Search memories using semantic similarity.

        Args:
            query: The search query
            entity_id: Filter by specific entity (optional)
            scope: Filter by memory scope (optional)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of matching memories with similarity scores
        """
        if not self.semantic_search.is_available():
            logger.warning(
                "Semantic search not available, falling back to text-based search"
            )
            return self._search_memories_text(query, entity_id, scope, limit)

        return self.semantic_search.search_memories(
            query=query,
            entity_id=entity_id,
            scope=scope,
            limit=limit,
            threshold=threshold,
        )

    def _search_memories_text(
        self,
        query: str,
        entity_id: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fallback text-based search when semantic search is not available.

        Args:
            query: The search query
            entity_id: Filter by specific entity (optional)
            scope: Filter by memory scope (optional)
            limit: Maximum number of results to return

        Returns:
            List of matching memories ranked by relevance
        """
        results = []

        # Search through all scoped memories
        for e_id, scopes in self.scoped_memory.items():
            # Skip if filtering by entity
            if entity_id and e_id != entity_id:
                continue

            for scope_name, visibilities in scopes.items():
                # Skip if filtering by scope
                if scope and scope_name != scope:
                    continue

                for visibility_name, memories in visibilities.items():
                    for memory in memories:
                        # Simple text matching (could be improved with better scoring)
                        content_lower = memory["content"].lower()
                        query_lower = query.lower()

                        if query_lower in content_lower:
                            relevance_score = len(query_lower) / len(
                                content_lower
                            )  # Simple relevance
                            results.append(
                                {
                                    "memory_id": f"{e_id}_{scope_name}_{memory['turn']}",
                                    "content": memory["content"],
                                    "similarity": relevance_score,
                                    "metadata": {
                                        "entity_id": e_id,
                                        "scope": scope_name,
                                        "visibility": visibility_name,
                                        "turn": memory["turn"],
                                        "importance": memory.get("importance", 5),
                                    },
                                }
                            )

        # Sort by relevance and limit
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def _convert_legacy_memories(self):
        """Convert legacy memory format to scoped format"""
        # Convert private memories
        for entity_id, memories in self.private_memory.items():
            for memory in memories:
                scope = memory.get("scope", "general")
                content = memory["content"]
                turn = memory["turn"]

                # Create scoped memory entry
                self.scoped_memory[entity_id][scope]["private"].append(
                    {
                        "content": content,
                        "scope": scope,
                        "visibility": "private",
                        "turn": turn,
                        "importance": 5,
                        "related_entities": [],
                    }
                )

        # Convert public memories
        for entity_id, memories in self.public_memory.items():
            for memory in memories:
                content = memory["content"]
                turn = memory["turn"]

                # Create scoped memory entry
                self.scoped_memory[entity_id]["general"]["public"].append(
                    {
                        "content": content,
                        "scope": "general",
                        "visibility": "public",
                        "turn": turn,
                        "importance": 5,
                        "related_entities": [],
                    }
                )

    def update_private_memory(
        self, entity_id: str, content: str, scope: str = "general"
    ):
        """Update private memory for an entity (legacy compatibility)"""
        # Use the new scoped memory system
        self.update_scoped_memory(
            entity_id=entity_id,
            scope=scope,  # type: ignore
            content=content,
            visibility="private",
        )

    def update_public_memory(self, entity_id: str, content: str):
        """Update public memory for an entity (legacy compatibility)"""
        # Use the new scoped memory system
        self.update_scoped_memory(
            entity_id=entity_id, scope="general", content=content, visibility="public"
        )

    def get_turn_count(self) -> int:
        """Get current turn count"""
        return self.turn_count

    def increment_turn(self):
        """Increment turn count"""
        self.turn_count += 1

    def save_to_database(self):
        """Save current memory state to database"""
        if self.db_manager:
            # Prepare scoped memory for storage (flatten for database compatibility)
            scoped_memory_flat = {}
            for entity_id, scopes in self.scoped_memory.items():
                entity_memories = []
                for scope_name, visibilities in scopes.items():
                    for visibility_name, memories in visibilities.items():
                        for memory in memories:
                            entity_memories.append(
                                {
                                    "content": memory["content"],
                                    "scope": memory["scope"],
                                    "visibility": memory["visibility"],
                                    "turn": memory["turn"],
                                    "importance": memory["importance"],
                                    "related_entities": memory["related_entities"],
                                }
                            )

                if entity_memories:
                    scoped_memory_flat[entity_id] = entity_memories

            self.db_manager.update_session(
                self.session_id,
                {
                    "private_memory": dict(self.private_memory),
                    "public_memory": dict(self.public_memory),
                    "scoped_memory": scoped_memory_flat,
                    "turn": self.turn_count,
                },
            )

    def get_memory_summary(self, entity_id: str, max_turns: int = 10) -> str:
        """Get a summary of recent memory for an entity"""

        private = self.private_memory.get(entity_id, [])
        public = self.public_memory.get(entity_id, [])

        # Get recent memory
        recent_private = [
            m for m in private if m["turn"] >= self.turn_count - max_turns
        ]
        recent_public = [m for m in public if m["turn"] >= self.turn_count - max_turns]

        summary = []
        if recent_private:
            summary.append(
                "Private thoughts: " + "; ".join([m["content"] for m in recent_private])
            )
        if recent_public:
            summary.append(
                "Public actions: " + "; ".join([m["content"] for m in recent_public])
            )

        return " | ".join(summary)
