"""
Simplified turn orchestrator for narrative-driven gameplay.

This orchestrator works with SimplifiedScenario instead of ScenarioSpec,
focusing on dynamic narrative generation without rigid rule systems.
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.db.manager import DatabaseManager
from backend.engine.memory import MemoryManager
from backend.prompts import NARRATOR_SYSTEM
from backend.providers import create_provider
from backend.schemas import Outcome
from backend.schemas.simplified import CharacterProfile, SimplifiedScenario
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SimplifiedOrchestrator:
    """
    Turn orchestrator for simplified narrative-driven scenarios.

    This orchestrator uses world backgrounds and character profiles to
    generate dynamic narratives without complex rule enforcement.
    """

    def __init__(self, scenario: SimplifiedScenario, session_id: str, db_manager=None):
        """
        Initialize the simplified orchestrator.

        Args:
            scenario: SimplifiedScenario with world and characters
            session_id: Unique session identifier
            db_manager: Database manager for persistence
        """
        self.scenario = scenario
        self.session_id = session_id
        self.db_manager = db_manager
        self.provider = create_provider()

        # Initialize memory system
        private_memory = {}
        public_memory = {}
        turn_count = 0

        if db_manager:
            session_data = db_manager.get_session(session_id)
            if session_data:
                private_memory = session_data.get("private_memory", {})
                public_memory = session_data.get("public_memory", {})
                turn_count = session_data.get("turn", 0)

        self.memory = MemoryManager(
            session_id, db_manager, private_memory, public_memory, turn_count
        )

        self._session_ref: Optional[Dict[str, Any]] = None

    def set_session_ref(self, session_ref: Dict[str, Any]):
        """
        Set reference to session data for accessing turn history.

        Args:
            session_ref: Dictionary containing session data
        """
        self._session_ref = session_ref

    async def process_turn(self, user_input: Optional[str] = None) -> Outcome:
        """
        Process a turn using simplified narrative generation.

        Args:
            user_input: Optional player action description

        Returns:
            Outcome with generated narrative
        """
        logger.info(
            f"[SimplifiedOrchestrator] Processing turn {self.memory.get_turn_count() + 1}"
        )

        try:
            # Build context from scenario and memory
            context = self._build_context()

            # Generate narrative using LLM
            narrative = await self._generate_narrative(context, user_input)

            # Create outcome
            outcome = Outcome(
                narrative=narrative,
                state_changes=[],  # State changes are optional in simplified mode
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
                emotional_state_updates=None,
                suggested_actions=self.scenario.suggested_actions,
            )

            # Increment turn counter
            self.memory.increment_turn()

            # Save memory
            if self.db_manager:
                self.memory.save_to_database()

            logger.info(
                f"[SimplifiedOrchestrator] Turn {self.memory.get_turn_count()} completed"
            )

            return outcome

        except Exception as e:
            logger.error(f"[SimplifiedOrchestrator] Turn processing failed: {e}")
            # Return fallback outcome
            return Outcome(
                narrative="The story continues...",
                state_changes=[],
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
                emotional_state_updates=None,
                suggested_actions=self.scenario.suggested_actions,
            )

    def _build_context(self) -> Dict[str, Any]:
        """
        Build context for narrative generation.

        Returns:
            Dictionary with scenario info, characters, and history
        """
        # Get POV character
        pov_id = self.scenario.initial_state.get("pov_entity", "player_character")

        # Get character info
        characters_info = []
        for char in self.scenario.characters:
            char_info = {
                "name": char.name,
                "id": char.id,
                "background": char.background[:300],  # Truncate for context
                "traits": char.personality_traits,
                "goals": char.goals,
            }
            characters_info.append(char_info)

        # Get recent turn history
        recent_turns = self._get_recent_turns(3)

        # Get memories for POV character
        pov_memories = []
        try:
            memories = self.memory.get_scoped_memory(
                entity_id=pov_id, scope=None, visibility="private", limit=5
            )
            for mem in memories:
                pov_memories.append(mem["content"])
        except Exception as e:
            logger.warning(f"Failed to retrieve memories: {e}")

        return {
            "world": self.scenario.world_background.description,
            "setting": self.scenario.world_background.setting,
            "tone": self.scenario.world_background.tone,
            "themes": self.scenario.world_background.themes,
            "characters": characters_info,
            "pov_character": pov_id,
            "recent_memories": pov_memories,
            "recent_turns": recent_turns,
            "turn": self.memory.get_turn_count(),
            "suggested_actions": self.scenario.suggested_actions,
            "difficulty": (
                self.scenario.difficulty_hints.get("difficulty", "balanced")
                if self.scenario.difficulty_hints
                else "balanced"
            ),
        }

    async def _generate_narrative(
        self, context: Dict[str, Any], user_input: Optional[str]
    ) -> str:
        """
        Generate narrative for the current turn.

        Args:
            context: Context dictionary with world and character info
            user_input: Player's action or None for continuation

        Returns:
            Generated narrative text
        """
        # Build system prompt
        system_prompt = f"""{NARRATOR_SYSTEM}

WORLD SETTING:
{context['world'][:500]}...

TONE: {context['tone']}
THEMES: {', '.join(context['themes'])}

CHARACTERS:
{self._format_characters(context['characters'][:3])}

You have creative freedom to develop the story naturally. Focus on:
- Vivid, engaging narrative
- Character development and interactions
- Building tension and interest
- Responding to player choices meaningfully
- Creating memorable moments

Suggested action types for this world: {', '.join(context['suggested_actions'])}"""

        # Build user prompt
        recent_turns_text = self._format_recent_turns(context["recent_turns"])
        memories_text = (
            "\n".join(context["recent_memories"][:3])
            if context["recent_memories"]
            else "No specific memories"
        )

        user_prompt = f"""CURRENT TURN: {context['turn'] + 1}

RECENT EVENTS:
{recent_turns_text}

{context['pov_character'].upper()}'S MEMORIES:
{memories_text}

PLAYER ACTION: {user_input or "Continue the story"}

Generate the next part of the story (2-4 paragraphs). Be creative and engaging.
Focus on narrative quality over rules. Create meaningful moments and character development."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.provider.chat(messages, max_tokens=800)
            narrative = response.content.strip()

            # Clean up any JSON artifacts if present
            if narrative.startswith("{") or narrative.startswith("["):
                logger.warning("Narrative appears to be JSON, attempting to extract")
                # Try to find narrative field
                try:
                    data = json.loads(narrative)
                    if isinstance(data, dict) and "narrative" in data:
                        narrative = data["narrative"]
                except:
                    pass

            return narrative

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return "The story continues in unexpected ways..."

    def _format_characters(self, characters: List[Dict[str, Any]]) -> str:
        """Format character info for prompt."""
        formatted = []
        for char in characters:
            formatted.append(
                f"- {char['name']} ({char['id']}): {', '.join(char['traits'][:3])}"
            )
        return "\n".join(formatted)

    def _format_recent_turns(self, recent_turns: List[Dict[str, Any]]) -> str:
        """Format recent turns for prompt."""
        if not recent_turns:
            return "This is the beginning of the story."

        formatted = []
        for turn in recent_turns:
            formatted.append(f"Turn {turn['turn']}: {turn.get('narrative', '')[:200]}")
        return "\n".join(formatted)

    def _get_recent_turns(self, n: int = 3) -> List[Dict[str, Any]]:
        """
        Get recent turns from session history.

        Args:
            n: Number of turns to retrieve

        Returns:
            List of recent turn records
        """
        if not self._session_ref or "turn_history" not in self._session_ref:
            return []

        turn_history = self._session_ref.get("turn_history", [])
        return turn_history[-n:] if len(turn_history) >= n else turn_history

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return self.memory.get_memory_statistics()
