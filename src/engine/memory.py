"""
Memory management for private and public entity memory
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict


class MemoryManager:
    """Manages private and public memory for entities"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.private_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.public_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.turn_count = 0
    
    def get_private_memory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get private memory for an entity"""
        return self.private_memory.get(entity_id, [])
    
    def get_public_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all public memory"""
        return dict(self.public_memory)
    
    def update_private_memory(self, entity_id: str, content: str, scope: str):
        """Update private memory for an entity"""
        self.private_memory[entity_id].append({
            "content": content,
            "scope": scope,
            "turn": self.turn_count
        })
    
    def update_public_memory(self, entity_id: str, content: str):
        """Update public memory for an entity"""
        self.public_memory[entity_id].append({
            "content": content,
            "turn": self.turn_count
        })
    
    def get_turn_count(self) -> int:
        """Get current turn count"""
        return self.turn_count
    
    def increment_turn(self):
        """Increment turn count"""
        self.turn_count += 1
    
    def clear_memory(self, entity_id: str = None):
        """Clear memory for an entity or all entities"""
        if entity_id:
            self.private_memory.pop(entity_id, None)
            self.public_memory.pop(entity_id, None)
        else:
            self.private_memory.clear()
            self.public_memory.clear()
    
    def get_memory_summary(self, entity_id: str, max_turns: int = 10) -> str:
        """Get a summary of recent memory for an entity"""
        
        private = self.private_memory.get(entity_id, [])
        public = self.public_memory.get(entity_id, [])
        
        # Get recent memory
        recent_private = [m for m in private if m["turn"] >= self.turn_count - max_turns]
        recent_public = [m for m in public if m["turn"] >= self.turn_count - max_turns]
        
        summary = []
        if recent_private:
            summary.append("Private thoughts: " + "; ".join([m["content"] for m in recent_private]))
        if recent_public:
            summary.append("Public actions: " + "; ".join([m["content"] for m in recent_public]))
        
        return " | ".join(summary)
