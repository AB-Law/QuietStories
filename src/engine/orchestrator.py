"""
Turn orchestrator - manages turn-based gameplay.

This module coordinates the game loop, managing:
- Context building from game state and history
- LLM narrative generation
- State updates and memory management
- Turn history tracking
"""

from typing import Dict, Any, List, Optional
import json
from langchain.schema import BaseMessage, SystemMessage, HumanMessage
from src.providers import create_provider
from src.schemas import Outcome, ScenarioSpec
from src.engine.compiler import ScenarioCompiler
from src.engine.memory import MemoryManager
from src.utils.jsonlogic import JSONLogicEvaluator
from src.prompts import NARRATOR_SYSTEM, NARRATOR_USER
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TurnOrchestrator:
    """
    Orchestrates turn-based gameplay with LLM integration.
    
    This class manages the game loop, building context from game state,
    turn history, and memory to generate coherent narratives. It implements
    smart context selection to keep LLM prompts focused and efficient.
    
    Attributes:
        spec: The scenario specification defining the game rules
        session_id: Unique identifier for this game session
        provider: LLM provider for narrative generation
        compiler: Compiler for scenario actions
        memory: Manager for entity memories
        tools: Compiled scenario actions (not used for narrator)
        _session_ref: Reference to fetch turn history
    """
    
    def __init__(self, spec: ScenarioSpec, session_id: str):
        """
        Initialize the turn orchestrator.
        
        Args:
            spec: Scenario specification defining game rules
            session_id: Unique session identifier
        """
        self.spec = spec
        self.session_id = session_id
        self.provider = create_provider()
        self.compiler = ScenarioCompiler(spec)
        self.memory = MemoryManager(session_id)
        self.tools = self.compiler.get_tools()
        self._session_ref = None  # Will be set to access session data
    
    def set_session_ref(self, session_ref: Dict[str, Any]):
        """
        Set reference to session data for accessing turn history.
        
        Args:
            session_ref: Dictionary containing session data including turn_history
        """
        self._session_ref = session_ref
    
    async def process_turn(self, user_input: str = None) -> Outcome:
        """
        Process a single turn of gameplay.
        
        This method:
        1. Builds context from state, history, and memory
        2. Generates narrative via LLM
        3. Applies state changes
        4. Updates memory
        5. Increments turn counter
        
        Args:
            user_input: Optional player action description
        
        Returns:
            Outcome object containing narrative and state changes
        
        Raises:
            Exception: If LLM call fails and fallback also fails
        """
        logger.info(f"[Orchestrator] Processing turn {self.memory.get_turn_count() + 1}")
        
        # Build context for the LLM
        context = self._build_context()
        
        # Create messages
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=self._get_user_prompt(context, user_input))
        ]
        
        logger.debug("[Orchestrator] Calling provider.chat with outcome schema")
        
        # Get response from LLM - don't pass scenario actions as tools
        # The narrator should use state_changes in the Outcome JSON instead
        response = await self.provider.chat(
            messages=messages,
            json_schema=self._get_outcome_schema()
        )
        logger.info("[Orchestrator] Provider returned; parsing outcome")
        
        # Check for empty content
        if not response.content or response.content.strip() == '':
            logger.error("[Orchestrator] Empty content from provider!")
            if response.tool_calls:
                logger.error(f"[Orchestrator] Provider tried to call tools: {[tc.get('function', {}).get('name') for tc in response.tool_calls]}")
            # Fallback to minimal outcome
            outcome = Outcome(
                narrative="The story continues...",
                state_changes=[]
            )
        else:
            # Parse and validate outcome
            logger.debug(f"[Orchestrator] Content preview: {response.content[:300]}")
            outcome = self._parse_outcome(response.content)
        
        # Apply state changes
        self._apply_state_changes(outcome.state_changes)
        
        # Update memory
        if outcome.hidden_memory_updates:
            self._update_memory(outcome.hidden_memory_updates)
        
        # Increment turn counter
        self.memory.increment_turn()
        logger.debug(f"[Orchestrator] Turn incremented to {self.memory.get_turn_count()}")
        
        return outcome
    
    def _build_context(self) -> Dict[str, Any]:
        """
        Build comprehensive context for the LLM narrator.
        
        This method assembles all relevant information for generating
        the next turn's narrative, using smart context selection to
        keep prompts focused and efficient.
        
        Returns:
            Dictionary containing:
                - state: Current game state
                - entities: Current entity list
                - recent_turns: Last 3 turns verbatim
                - history_summary: Summary of older turns
                - private_memory: POV entity's private memories
                - public_memory: All public memories
                - turn: Current turn number
                - available_actions: Actions available to player
                - world_background: World setting (if available)
        
        Note:
            Context selection prioritizes recent information and
            summarizes older content to fit within LLM context limits.
        """
        # Get POV entity's private memory + all public memory
        pov_entity = self._get_pov_entity()
        private_memory = self.memory.get_private_memory(pov_entity)
        public_memory = self.memory.get_public_memory()
        
        # Get turn history for context
        recent_turns = self._get_recent_turns(3)  # Last 3 turns verbatim
        history_summary = self._get_history_summary()  # Summarized older turns
        
        # Get world background if available
        world_background = None
        if self._session_ref and 'world_background' in self._session_ref:
            world_background = self._session_ref['world_background']
        
        return {
            "state": self.spec.state,
            "entities": self.spec.entities,
            "recent_turns": recent_turns,
            "history_summary": history_summary,
            "private_memory": private_memory,
            "public_memory": public_memory,
            "turn": self.memory.get_turn_count(),
            "available_actions": self._get_available_actions(),
            "world_background": world_background
        }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the narrator"""
        return NARRATOR_SYSTEM
    
    def _get_user_prompt(self, context: Dict[str, Any], user_input: str = None) -> str:
        """
        Generate user prompt with full context for narrator.
        
        Args:
            context: Context dictionary from _build_context()
            user_input: Optional player action description
        
        Returns:
            Formatted prompt string with all relevant context
        
        Note:
            This method formats context into a narrative-friendly structure,
            prioritizing recent events and current state information.
        """
        state_summary = json.dumps(context['state'], indent=2)
        
        # Format recent turns
        recent_turns_text = ""
        if context.get('recent_turns'):
            turns_list = []
            for turn in context['recent_turns']:
                turns_list.append(f"Turn {turn['turn']}: {turn.get('user_action', 'Continue')}")
                turns_list.append(f"  Narrative: {turn['narrative'][:200]}...")
            recent_turns_text = "\n".join(turns_list)
        else:
            recent_turns_text = "No previous turns"
        
        # Format history summary
        history_text = context.get('history_summary', "This is the beginning of the story")
        
        # Format entities
        entities_text = ""
        if context.get('entities'):
            entities_list = [
                f"- {e.get('id', 'unknown')}: {e.get('type', 'entity')}"
                for e in context['entities'][:10]
            ]
            entities_text = "\n".join(entities_list)
        else:
            entities_text = "No entities yet"
        
        # Format world background
        world_text = context.get('world_background', "No world background available")
        
        # Build complete prompt
        return NARRATOR_USER.format(
            state_summary=state_summary,
            world_background=world_text[:500] if world_text else "Unknown",
            recent_turns=recent_turns_text,
            history_summary=history_text,
            entities_summary=entities_text,
            action=user_input or "Continue the story"
        )
    
    def _get_outcome_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for outcome validation.
        
        Returns:
            JSON schema generated from Pydantic Outcome model
        """
        # Use Pydantic's generated schema for accuracy
        return Outcome.model_json_schema()
    
    def _get_recent_turns(self, n: int = 3) -> List[Dict[str, Any]]:
        """
        Fetch the last N turns from session history.
        
        Args:
            n: Number of recent turns to retrieve (default: 3)
        
        Returns:
            List of turn records, most recent last. Empty list if no history.
        
        Note:
            This method fetches from the session stored in _session_ref.
            If _session_ref is not set, returns empty list.
        """
        if not self._session_ref or 'turn_history' not in self._session_ref:
            return []
        
        turn_history = self._session_ref.get('turn_history', [])
        if not turn_history:
            return []
        
        # Return last N turns
        recent = turn_history[-n:] if len(turn_history) >= n else turn_history
        logger.debug(f"Retrieved {len(recent)} recent turns")
        return recent
    
    def _get_history_summary(self) -> str:
        """
        Get a summary of older turns (beyond the recent 3).
        
        Returns:
            A summary string of historical events, or empty string if not enough history
        
        Note:
            This method summarizes turns in batches of 5 to keep context manageable.
            Only summarizes turns older than the last 3 (handled by _get_recent_turns).
        """
        if not self._session_ref or 'turn_history' not in self._session_ref:
            return ""
        
        turn_history = self._session_ref.get('turn_history', [])
        
        # Only summarize if we have more than 3 turns
        if len(turn_history) <= 3:
            return ""
        
        # Get turns to summarize (all except last 3)
        older_turns = turn_history[:-3]
        
        if not older_turns:
            return ""
        
        # Simple summarization: extract key events every 5 turns
        summary_points = []
        for i in range(0, len(older_turns), 5):
            batch = older_turns[i:i+5]
            # Extract narrative highlights from batch
            highlights = [
                f"Turn {turn['turn']}: {turn.get('user_action', 'continued')}"
                for turn in batch[:2]  # Just first 2 of each batch
            ]
            summary_points.extend(highlights)
        
        if summary_points:
            summary = "Earlier events: " + "; ".join(summary_points[:10])  # Limit to 10 points
            logger.debug(f"Generated history summary with {len(summary_points)} points")
            return summary
        
        return ""
    
    async def _summarize_turns(self, turns: List[Dict[str, Any]]) -> str:
        """
        Use LLM to summarize a batch of turns.
        
        Args:
            turns: List of turn records to summarize
        
        Returns:
            A concise summary paragraph
        
        Note:
            This method is currently not used (simple summarization in _get_history_summary
            is sufficient). Can be activated for more sophisticated summarization if needed.
        """
        if not turns:
            return ""
        
        # Build summary request
        turns_text = []
        for turn in turns:
            turns_text.append(f"Turn {turn['turn']}: {turn.get('user_action', 'Continue')}")
            turns_text.append(f"Result: {turn['narrative'][:150]}...")
        
        prompt = f"""Summarize these game turns into 2-3 concise sentences capturing key events:

{chr(10).join(turns_text)}

Summary:"""
        
        messages = [
            SystemMessage(content="You are a concise summarizer. Create brief event summaries."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = await self.provider.chat(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Turn summarization failed: {e}")
            return f"Events during turns {turns[0]['turn']}-{turns[-1]['turn']}"
    
    def _parse_outcome(self, content: str) -> Outcome:
        """Parse and validate outcome from LLM response"""
        
        import json
        import re
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Clean up content - remove double curly braces if present
            content = content.strip()
            
            # Fix double curly braces ({{ -> {, }} -> })
            if content.startswith('{{') and content.endswith('}}'):
                logger.debug("Removing double curly braces from content")
                content = content[1:-1]  # Remove first and last character
            
            # Try to parse JSON directly
            outcome_data = json.loads(content)
            logger.debug(f"Successfully parsed outcome: {list(outcome_data.keys())}")
            return Outcome(**outcome_data)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
            logger.debug(f"Content preview: {content[:200]}")
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    outcome_data = json.loads(json_str)
                    logger.info("Successfully extracted and parsed JSON from response")
                    return Outcome(**outcome_data)
                except Exception as e2:
                    logger.error(f"JSON extraction failed: {e2}")
            # Fallback to minimal outcome
            logger.warning("Falling back to minimal outcome")
            return Outcome(
                narrative="The story continues...",
                state_changes=[]
            )
        except Exception as e:
            logger.error(f"Outcome parsing error: {e}", exc_info=True)
            # Fallback to minimal outcome
            return Outcome(
                narrative="The story continues...",
                state_changes=[]
            )
    
    def _apply_state_changes(self, state_changes: List[Any]):
        """
        Apply state changes to the scenario state.
        
        Args:
            state_changes: List of StateChange objects or dicts
        
        Note:
            Handles both Pydantic StateChange objects and plain dicts
            for flexibility. Updates self.spec.state in place.
        """
        for change in state_changes:
            try:
                evaluator = JSONLogicEvaluator()
                
                # Handle both StateChange objects and dicts
                if hasattr(change, 'op'):
                    # Pydantic object
                    op = change.op
                    path = change.path if hasattr(change, 'path') else ""
                    value = change.value if hasattr(change, 'value') else None
                else:
                    # Dict
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
                        
                        # Detect entity creation
                        if "entities" in path or "entity" in path:
                            entity_id = value.get('id', 'unknown') if isinstance(value, dict) else 'unknown'
                            logger.info(f"New entity created: {entity_id}")
                            # Also update spec.entities if it's the main entities list
                            if path.endswith('entities') and isinstance(value, dict):
                                self.spec.entities.append(value)
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
        """
        Update entity memories from hidden memory updates.
        
        Args:
            memory_updates: List of memory update dictionaries from Outcome
        
        Note:
            Processes hidden_memory_updates from the narrator's Outcome,
            routing them to private or public memory based on visibility.
            Each update should have: target_id, content, scope, visibility.
        """
        for update in memory_updates:
            target_id = update.get("target_id")
            content = update.get("content")
            scope = update.get("scope", "general")
            visibility = update.get("visibility", "private")
            
            if not target_id or not content:
                logger.warning(f"Skipping invalid memory update: {update}")
                continue
            
            # Route to appropriate memory based on visibility
            if visibility == "private":
                self.memory.update_private_memory(target_id, content, scope)
                logger.debug(f"Updated private memory for {target_id}")
            elif visibility == "public":
                self.memory.update_public_memory(target_id, content)
                logger.debug(f"Updated public memory for {target_id}")
            else:
                logger.warning(f"Unknown visibility '{visibility}', treating as private")
                self.memory.update_private_memory(target_id, content, scope)
    
    def _get_pov_entity(self) -> str:
        """
        Get the point-of-view entity ID for the current session.
        
        Returns:
            Entity ID string (currently defaults to "player")
        
        Note:
            Current implementation is simplified. In production, this could:
            - Read from session state
            - Support multiple player entities
            - Handle entity switching mid-game
            - Detect from entity list
        
        TODO: Implement proper POV detection from session/state
        """
        # Check if there's a POV marker in state
        if hasattr(self.spec, 'state') and isinstance(self.spec.state, dict):
            pov = self.spec.state.get('pov_entity')
            if pov:
                return pov
        
        # Check if there's a player entity in entities list
        if self.spec.entities:
            for entity in self.spec.entities:
                if entity.get('type') == 'player' or entity.get('id') == 'player':
                    return entity.get('id', 'player')
        
        # Default to "player"
        return "player"
    
    def _get_available_actions(self) -> List[str]:
        """
        Get list of available action IDs for the current state.
        
        Returns:
            List of action ID strings
        
        Note:
            Current implementation returns all actions. In production,
            this should filter by:
            - Preconditions against current state
            - Location/context restrictions
            - Entity capabilities
        
        TODO: Implement precondition checking
        """
        # TODO: Filter actions by preconditions
        # For now, return all action IDs
        action_ids = [action.id for action in self.spec.actions]
        
        # Future: check preconditions
        # available = []
        # for action in self.spec.actions:
        #     if self._check_preconditions(action.preconditions, self.spec.state):
        #         available.append(action.id)
        # return available
        
        return action_ids
