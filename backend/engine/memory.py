"""
Enhanced memory management for scoped entity memory types
"""

from collections import defaultdict
from typing import Any, Dict, List, Literal, Optional

# Define valid memory scopes
MemoryScope = Literal["belief", "relationship", "event", "location", "goal", "general"]

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
