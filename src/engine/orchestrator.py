"""
Turn orchestrator - manages turn-based gameplay
"""

from typing import Dict, Any, List, Optional
from langchain.schema import BaseMessage, SystemMessage, HumanMessage
from src.providers import create_provider
from src.schemas import Outcome, ScenarioSpec
from src.engine.compiler import ScenarioCompiler
from src.engine.memory import MemoryManager
from src.utils.jsonlogic import JSONLogicEvaluator


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
        import re
        
        try:
            # Try to parse JSON directly
            outcome_data = json.loads(content)
            return Outcome(**outcome_data)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    outcome_data = json.loads(json_str)
                    return Outcome(**outcome_data)
                except Exception as e2:
                    print(f"JSON extraction failed: {e2}")
            # Fallback to minimal outcome
            return Outcome(
                narrative="The story continues...",
                state_changes=[]
            )
        except Exception as e:
            print(f"Outcome parsing error: {e}")
            # Fallback to minimal outcome
            return Outcome(
                narrative="The story continues...",
                state_changes=[]
            )
    
    def _apply_state_changes(self, state_changes: List[Dict[str, Any]]):
        """Apply state changes to the scenario state"""
        
        for change in state_changes:
            try:
                evaluator = JSONLogicEvaluator()
                
                op = change.get("op")
                path = change.get("path", "")
                value = change.get("value")
                
                if op == "set":
                    self._set_value_at_path(path, value)
                elif op == "inc":
                    current_value = self._get_value_at_path(path)
                    self._set_value_at_path(path, current_value + value)
                elif op == "dec":
                    current_value = self._get_value_at_path(path)
                    self._set_value_at_path(path, current_value - value)
                elif op == "mul":
                    current_value = self._get_value_at_path(path)
                    self._set_value_at_path(path, current_value * value)
                elif op == "patch":
                    current_value = self._get_value_at_path(path)
                    if isinstance(current_value, dict) and isinstance(value, dict):
                        current_value.update(value)
                        self._set_value_at_path(path, current_value)
                elif op == "push":
                    current_value = self._get_value_at_path(path)
                    if isinstance(current_value, list):
                        current_value.append(value)
                        self._set_value_at_path(path, current_value)
                elif op == "pop":
                    current_value = self._get_value_at_path(path)
                    if isinstance(current_value, list) and len(current_value) > 0:
                        current_value.pop()
                        self._set_value_at_path(path, current_value)
                elif op == "addlog":
                    # Add to log list
                    log_path = path if path else "state.log"
                    current_log = self._get_value_at_path(log_path)
                    if isinstance(current_log, list):
                        current_log.append(value)
                        self._set_value_at_path(log_path, current_log)
                    else:
                        self._set_value_at_path(log_path, [value])
                        
            except Exception as e:
                # Log error but continue with other changes
                print(f"Error applying state change {change}: {e}")
    
    def _get_value_at_path(self, path: str) -> Any:
        """Get value at JSON pointer path"""
        if not path or path == "":
            return self.spec.state
        
        # Simple path resolution - in production, use proper JSON pointer library
        parts = path.split(".")
        current = self.spec.state
        
        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                # Array access
                index = int(part[1:-1])
                current = current[index]
            else:
                current = current.get(part, {})
        
        return current
    
    def _set_value_at_path(self, path: str, value: Any):
        """Set value at JSON pointer path"""
        if not path or path == "":
            self.spec.state = value
            return
        
        # Simple path resolution - in production, use proper JSON pointer library
        parts = path.split(".")
        current = self.spec.state
        
        for i, part in enumerate(parts[:-1]):
            if part.startswith("[") and part.endswith("]"):
                # Array access
                index = int(part[1:-1])
                current = current[index]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        # Set the final value
        final_part = parts[-1]
        if final_part.startswith("[") and final_part.endswith("]"):
            index = int(final_part[1:-1])
            current[index] = value
        else:
            current[final_part] = value
    
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
