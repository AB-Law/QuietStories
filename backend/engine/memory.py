"""
Memory management for private and public entity memory
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional


class MemoryManager:
    """Manages private and public memory for entities"""

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
        self.private_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.public_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.turn_count = initial_turn_count

        # Load initial memory if provided
        if initial_private_memory:
            for entity_id, memories in initial_private_memory.items():
                self.private_memory[entity_id] = memories
        if initial_public_memory:
            for entity_id, memories in initial_public_memory.items():
                self.public_memory[entity_id] = memories

    def get_private_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get private memory for an entity"""
        return self.private_memory.get(entity_id, [])

    def get_public_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all public memory"""
        return dict(self.public_memory)

    def update_private_memory(self, entity_id: str, content: str, scope: str):
        """Update private memory for an entity"""
        self.private_memory[entity_id].append(
            {"content": content, "scope": scope, "turn": self.turn_count}
        )

    def update_public_memory(self, entity_id: str, content: str):
        """Update public memory for an entity"""
        self.public_memory[entity_id].append(
            {"content": content, "turn": self.turn_count}
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
            self.db_manager.update_session(
                self.session_id,
                {
                    "private_memory": dict(self.private_memory),
                    "public_memory": dict(self.public_memory),
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
