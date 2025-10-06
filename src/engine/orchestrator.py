"""
Turn orchestrator - manages turn-based gameplay
"""

from typing import Dict, Any, List, Optional
from langchain.schema import BaseMessage, SystemMessage, HumanMessage
from ..providers import create_provider
from ..schemas import Outcome, ScenarioSpec
from .compiler import ScenarioCompiler
from .memory import MemoryManager


class TurnOrchestrator:
    """Orchestrates turn-based gameplay with LLM integration"""
    
    def __init__(self, spec: ScenarioSpec, session_id: str):
        self.spec = spec
        self.session_id = session_id
        self.provider = create_provider()
        self.compiler = ScenarioCompiler(spec)
        self.memory = MemoryManager(session_id)
        self.tools = self.compiler.get_tools()
    
    async def process_turn(self, user_input: str = None) -> Outcome:
        """Process a single turn"""
        
        # Build context for the LLM
        context = self._build_context()
        
        # Create messages
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=self._get_user_prompt(context, user_input))
        ]
        
        # Get response from LLM with tools
        response = await self.provider.chat(
            messages=messages,
            tools=self.tools,
            json_schema=self._get_outcome_schema()
        )
        
        # Parse and validate outcome
        outcome = self._parse_outcome(response.content)
        
        # Apply state changes
        self._apply_state_changes(outcome.state_changes)
        
        # Update memory
        if outcome.hidden_memory_updates:
            self._update_memory(outcome.hidden_memory_updates)
        
        return outcome
    
    def _build_context(self) -> Dict[str, Any]:
        """Build context for the LLM"""
        
        # Get POV entity's private memory + all public memory
        pov_entity = self._get_pov_entity()
        private_memory = self.memory.get_private_memory(pov_entity)
        public_memory = self.memory.get_public_memory()
        
        return {
            "state": self.spec.state,
            "entities": self.spec.entities,
            "private_memory": private_memory,
            "public_memory": public_memory,
            "turn": self.memory.get_turn_count(),
            "available_actions": self._get_available_actions()
        }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the narrator"""
        
        return """ROLE: Narrator & Referee.
Use provided tools for all reads/writes.
Never reveal inner thoughts of non-POV entities.
Return valid Outcome JSON only. If uncertain, add a roll_requests entry.

You are the narrator of an interactive story. You must:
1. Provide engaging narrative based on the current state
2. Use available tools to interact with the world
3. Never reveal private thoughts of non-POV entities
4. Return valid JSON matching the Outcome schema
5. Add roll_requests when uncertainty requires dice rolls"""
    
    def _get_user_prompt(self, context: Dict[str, Any], user_input: str = None) -> str:
        """Get user prompt with context"""
        
        prompt = f"""Current State:
{context['state']}

Available Actions: {context['available_actions']}

Turn: {context['turn']}

"""
        
        if user_input:
            prompt += f"User Action: {user_input}\n\n"
        
        prompt += "Provide the next turn's outcome as valid JSON."
        
        return prompt
    
    def _get_outcome_schema(self) -> Dict[str, Any]:
        """Get JSON schema for outcome validation"""
        
        return {
            "type": "object",
            "properties": {
                "narrative": {"type": "string"},
                "visible_dialogue": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity_id": {"type": "string"},
                            "utterance": {"type": "string"}
                        }
                    }
                },
                "state_changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string"},
                            "path": {"type": "string"},
                            "value": {}
                        }
                    }
                },
                "roll_requests": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string"},
                            "target": {"type": "string"},
                            "difficulty": {"type": "integer"}
                        }
                    }
                }
            },
            "required": ["narrative", "state_changes"]
        }
    
    def _parse_outcome(self, content: str) -> Outcome:
        """Parse and validate outcome from LLM response"""
        
        import json
        
        try:
            outcome_data = json.loads(content)
            return Outcome(**outcome_data)
        except Exception as e:
            # Fallback to minimal outcome
            return Outcome(
                narrative="The story continues...",
                state_changes=[]
            )
    
    def _apply_state_changes(self, state_changes: List[Dict[str, Any]]):
        """Apply state changes to the scenario state"""
        
        for change in state_changes:
            # Simplified state update - in production, implement proper JSON pointer resolution
            if change["op"] == "set":
                # Set value at path
                pass
            elif change["op"] == "inc":
                # Increment value at path
                pass
            # ... other operations
    
    def _update_memory(self, memory_updates: List[Dict[str, Any]]):
        """Update memory with hidden updates"""
        
        for update in memory_updates:
            self.memory.update_private_memory(
                update["target_id"],
                update["content"],
                update["scope"]
            )
    
    def _get_pov_entity(self) -> str:
        """Get the point-of-view entity ID"""
        
        # Simplified - in production, this would be more sophisticated
        return "player"
    
    def _get_available_actions(self) -> List[str]:
        """Get list of available action IDs"""
        
        return [action.id for action in self.spec.actions]
