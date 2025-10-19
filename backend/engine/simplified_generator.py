"""
Simplified scenario generator focusing on narrative elements.

This module replaces the complex ScenarioSpec generation with a simpler
approach that generates world backgrounds and character profiles using LLMs.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.providers import create_provider
from backend.schemas.simplified import (
    CharacterMemory,
    CharacterProfile,
    SimplifiedScenario,
    WorldBackground,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SimplifiedScenarioGenerator:
    """
    Generates simplified scenarios focusing on narrative elements.

    This generator creates rich world backgrounds and character profiles
    without the complexity of JSONLogic rules and Monte Carlo simulations.
    """

    def __init__(self):
        """Initialize the generator with an LLM provider."""
        self.provider = create_provider()

    async def generate_scenario(
        self,
        description: str,
        num_characters: int = 3,
        include_player: bool = True,
        player_name: Optional[str] = None,
        difficulty: str = "balanced",
    ) -> SimplifiedScenario:
        """
        Generate a simplified scenario from a description.

        Args:
            description: Free-text scenario description
            num_characters: Number of characters to generate
            include_player: Whether to include a player character
            player_name: Optional player character name
            difficulty: Difficulty preference (easy, balanced, hard)

        Returns:
            SimplifiedScenario with world background and character profiles
        """
        logger.info(f"Generating simplified scenario from description")
        logger.debug(f"Parameters: chars={num_characters}, difficulty={difficulty}")

        try:
            # Generate world background
            logger.debug("Step 1: Generating world background...")
            world_background = await self._generate_world_background(
                description, difficulty
            )
            logger.info("World background generated successfully")

            # Generate character profiles
            logger.debug(f"Step 2: Generating {num_characters} character profiles...")
            characters = await self._generate_characters(
                description,
                world_background,
                num_characters,
                include_player,
                player_name,
            )
            logger.info(f"Generated {len(characters)} character profiles")

            # Extract scenario name from description or world background
            scenario_name = await self._extract_scenario_name(
                description, world_background
            )

            # Create suggested action types (not rigid rules)
            suggested_actions = self._generate_suggested_actions(world_background)

            # Build the simplified scenario
            scenario = SimplifiedScenario(
                id=str(uuid.uuid4()),
                name=scenario_name,
                description=description,
                world_background=world_background,
                characters=characters,
                initial_state={
                    "location": "starting_location",
                    "turn": 0,
                    "pov_entity": player_name
                    or (characters[0].id if characters else "player"),
                },
                difficulty_hints={
                    "difficulty": difficulty,
                    "challenge_level": "balanced",
                    "tone": world_background.tone,
                },
                suggested_actions=suggested_actions,
                created_at=datetime.utcnow().isoformat(),
                status="generated",
            )

            logger.info(f"✓ Simplified scenario generated: {scenario.name}")
            return scenario

        except Exception as e:
            logger.error(f"Failed to generate simplified scenario: {e}", exc_info=True)
            raise

    async def _generate_world_background(
        self, description: str, difficulty: str
    ) -> WorldBackground:
        """
        Generate rich world background from description.

        Args:
            description: User's scenario description
            difficulty: Difficulty preference

        Returns:
            WorldBackground with detailed narrative
        """
        system_prompt = """You are a world-building expert for interactive stories.
Generate rich, immersive world backgrounds that set the stage for adventures.

Create a detailed world description (3-5 paragraphs) that includes:
- Setting and time period
- Atmosphere and mood
- Key locations or areas
- Important factions, groups, or forces
- Current tensions, conflicts, or mysteries
- Sensory details and vivid imagery

Be specific and evocative, but leave room for player agency and discovery.
Return your response as JSON with this structure:
{
  "description": "3-5 paragraph world description",
  "themes": ["theme1", "theme2", "theme3"],
  "setting": "time period and location",
  "key_locations": ["location1", "location2"],
  "factions": ["faction1", "faction2"],
  "tone": "tone description"
}"""

        user_prompt = f"""Generate a world background for this scenario:

SCENARIO DESCRIPTION:
{description}

DIFFICULTY: {difficulty}

Create a compelling world that supports this scenario. Make it vivid and immersive.
Output ONLY valid JSON."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.provider.chat(messages)
            content = response.content.strip()

            # Parse JSON response
            if content.startswith("```"):
                # Remove markdown code blocks
                content = content.replace("```json", "").replace("```", "").strip()

            world_data = json.loads(content)

            # Validate and create WorldBackground
            return WorldBackground(**world_data)

        except Exception as e:
            logger.warning(f"World background generation failed: {e}")
            # Fallback to basic world background
            return WorldBackground(
                description=f"You find yourself in a world described as: {description}",
                themes=["adventure", "exploration"],
                setting="Unknown setting",
                key_locations=["Starting location"],
                factions=[],
                tone="balanced",
            )

    async def _generate_characters(
        self,
        description: str,
        world_background: WorldBackground,
        num_characters: int,
        include_player: bool,
        player_name: Optional[str],
    ) -> List[CharacterProfile]:
        """
        Generate character profiles for the scenario.

        Args:
            description: Scenario description
            world_background: Generated world background
            num_characters: Number of characters to generate
            include_player: Whether to include player character
            player_name: Optional player name

        Returns:
            List of CharacterProfile objects
        """
        system_prompt = """You are a character creation expert for interactive stories.
Generate rich, memorable characters with detailed backgrounds.

For each character, create:
- A proper name (not generic like "character_1" or "npc_1")
- Detailed background story (2-3 paragraphs, 200-400 words)
- Personality traits (3-5 traits)
- Goals and motivations (2-3 goals)
- Key relationships with other characters
- Optional: character stats if relevant

Return your response as JSON array:
[
  {
    "id": "character_id",
    "name": "Character Name",
    "type": "character",
    "background": "Detailed background story...",
    "personality_traits": ["trait1", "trait2"],
    "goals": ["goal1", "goal2"],
    "relationships": {},
    "stats": {}
  }
]"""

        player_instruction = ""
        if include_player and player_name:
            player_instruction = f"\n\nIMPORTANT: The FIRST character must be the player character named '{player_name}' with id 'player_character'."

        user_prompt = f"""Generate {num_characters} characters for this scenario:

SCENARIO: {description}

WORLD BACKGROUND:
{world_background.description[:500]}...

SETTING: {world_background.setting}
TONE: {world_background.tone}
{player_instruction}

Create diverse, interesting characters that fit this world.
Each character should have:
- A unique, fitting name (avoid generic numbered names)
- Rich background that connects to the world
- Clear personality and motivations
- Potential for interesting interactions

Output ONLY valid JSON array."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.provider.chat(messages, max_tokens=2000)
            content = response.content.strip()

            # Parse JSON response
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            characters_data = json.loads(content)

            # Create CharacterProfile objects
            characters = []
            for char_data in characters_data:
                # Add default memories if not present
                if "memories" not in char_data:
                    char_data["memories"] = []

                # Ensure type is set
                if "type" not in char_data:
                    char_data["type"] = "character"

                characters.append(CharacterProfile(**char_data))

            return characters

        except Exception as e:
            logger.warning(f"Character generation failed: {e}")
            # Fallback to minimal character set
            fallback_characters = []

            if include_player:
                fallback_characters.append(
                    CharacterProfile(
                        id="player_character",
                        name=player_name or "Hero",
                        type="character",
                        background="You are the protagonist of this story.",
                        personality_traits=["brave", "curious"],
                        goals=["Explore the world", "Overcome challenges"],
                        stats=None,
                    )
                )

            return fallback_characters

    async def _extract_scenario_name(
        self, description: str, world_background: WorldBackground
    ) -> str:
        """
        Extract or generate a concise scenario name.

        Args:
            description: User's description
            world_background: Generated world background

        Returns:
            A concise scenario name
        """
        system_prompt = """You create concise, evocative titles for interactive stories.
Generate a short title (2-5 words) that captures the essence of the scenario.
Return ONLY the title, nothing else."""

        user_prompt = f"""Create a title for this scenario:

DESCRIPTION: {description}

SETTING: {world_background.setting}
THEMES: {', '.join(world_background.themes)}

Generate a concise, memorable title (2-5 words):"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.provider.chat(messages, max_tokens=50)
            name = response.content.strip().strip("\"'")
            return name if name else "Untitled Adventure"

        except Exception as e:
            logger.warning(f"Name extraction failed: {e}")
            # Simple fallback: use first few words of description
            words = description.split()[:3]
            return " ".join(words).title()

    def _generate_suggested_actions(
        self, world_background: WorldBackground
    ) -> List[str]:
        """
        Generate suggested action types based on the world.

        These are not rigid rules but hints for the narrator about what
        kinds of actions make sense in this world.

        Args:
            world_background: The world background

        Returns:
            List of suggested action type keywords
        """
        # Base actions that work in most scenarios
        suggested = ["explore", "interact", "investigate"]

        # Add context-specific suggestions based on tone and themes
        if "dark" in world_background.tone.lower():
            suggested.extend(["survive", "hide", "fight"])
        elif "light" in world_background.tone.lower():
            suggested.extend(["help", "befriend", "celebrate"])

        # Add theme-based suggestions
        themes_lower = [t.lower() for t in world_background.themes]
        if "magic" in themes_lower or "fantasy" in themes_lower:
            suggested.extend(["cast spell", "enchant"])
        if "combat" in themes_lower or "war" in themes_lower:
            suggested.extend(["attack", "defend", "strategize"])
        if "mystery" in themes_lower or "investigation" in themes_lower:
            suggested.extend(["search", "deduce", "interrogate"])
        if "social" in themes_lower or "politics" in themes_lower:
            suggested.extend(["persuade", "negotiate", "ally"])

        # Return unique suggestions
        return list(set(suggested))
