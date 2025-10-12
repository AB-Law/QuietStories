"""
Session initializer for generating world state and entity backgrounds.

This module creates rich, detailed world narratives and character backgrounds
when a new game session starts, enhancing the player's immersion.
"""

import json
from typing import Any, Dict, List

from langchain.schema import HumanMessage, SystemMessage

from backend.providers import create_provider
from backend.schemas import ScenarioSpec
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SessionInitializer:
    """
    Initializes new game sessions with generated world and entity content.

    This class uses an LLM to generate:
    - Detailed world background narratives
    - Rich character backgrounds for entities
    - Initial setting descriptions

    Attributes:
        provider: LLM provider for content generation
    """

    def __init__(self):
        """Initialize the session initializer with an LLM provider."""
        self.provider = create_provider()

    async def initialize_session(
        self,
        spec: ScenarioSpec,
        session_id: str,
        num_characters: int = 3,
        generate_world: bool = True,
        generate_entities: bool = True,
    ) -> Dict[str, Any]:
        """
        Initialize a new session with generated world and entity content.

        Args:
            spec: The scenario specification to initialize from
            session_id: Unique identifier for this session
            num_characters: Number of entity backgrounds to generate (default: 3)
            generate_world: Whether to generate world background (default: True)
            generate_entities: Whether to generate entity backgrounds (default: True)

        Returns:
            Dictionary containing:
                - world_background: Narrative description of the world
                - entities: List of entities with generated backgrounds
                - initial_memories: Any initial memory entries

        Example:
            >>> initializer = SessionInitializer()
            >>> init_data = await initializer.initialize_session(
            ...     spec, "session_123", num_characters=5, generate_world=True
            ... )
            >>> print(init_data['world_background'])
            "The year is 2142. Mars has been terraformed..."
        """
        logger.info(f"Initializing session {session_id} for scenario: {spec.name}")
        logger.debug(
            f"Config: {num_characters} chars, world={generate_world}, entities={generate_entities}"
        )

        try:
            # Generate world background narrative if enabled
            if generate_world:
                logger.debug("Generating world background...")
                world_background = await self._generate_world_background(spec)
                logger.info(
                    f"World background generated ({len(world_background)} chars)"
                )
            else:
                world_background = (
                    f"Welcome to {spec.name}. Your adventure begins here."
                )
                logger.debug("Skipped world background generation (disabled in config)")

            # Expand entities with rich backgrounds if enabled
            if generate_entities and spec.entities:
                logger.debug(
                    f"Generating backgrounds for up to {num_characters} entities..."
                )
                detailed_entities = await self._generate_entity_backgrounds(
                    spec.entities, spec, world_background, max_entities=num_characters
                )
                logger.info(
                    f"Generated backgrounds for {len(detailed_entities)} entities"
                )
            else:
                detailed_entities = spec.entities
                logger.debug(
                    "Skipped entity background generation (disabled in config or no entities)"
                )

            return {
                "world_background": world_background,
                "entities": detailed_entities,
                "initial_memories": [],
            }
        except Exception as e:
            logger.error(f"Session initialization failed: {e}", exc_info=True)
            # Return minimal data on failure
            return {
                "world_background": f"Welcome to {spec.name}. Your adventure begins here.",
                "entities": spec.entities,
                "initial_memories": [],
            }

    async def _generate_world_background(self, spec: ScenarioSpec) -> str:
        """
        Generate a detailed world background narrative.

        Args:
            spec: The scenario specification

        Returns:
            A narrative description of the world setting (2-4 paragraphs)

        Note:
            This method attempts to extract context from the scenario spec
            including state, entities, and loss conditions to inform the narrative.
        """
        # Build context from scenario
        context = {
            "name": spec.name,
            "state": spec.state,
            "entities": [e.get("type") for e in spec.entities[:5]],
            "actions": [a.id for a in spec.actions[:5]],
            "themes": self._extract_themes(spec),
        }

        system_prompt = """You are a world-building expert. Generate rich, immersive world backgrounds
for interactive stories. Create 2-4 paragraphs describing the setting, atmosphere, and key context.

Focus on:
- Setting and time period
- Political/social climate
- Key factions or groups
- Current tensions or conflicts
- Atmosphere and mood

Be specific and vivid, but concise. No meta-commentary."""

        actions_list = context.get("actions") or []
        key_actions = actions_list[:3] if actions_list else []  # type: ignore

        user_prompt = f"""Generate a world background for this scenario:

Name: {context['name']}
Entity types: {', '.join(str(e) for e in context['entities'] if e is not None) if context['entities'] else 'None yet'}
Key actions: {', '.join(str(a) for a in key_actions if a is not None)}
Themes: {', '.join(str(t) for t in context['themes'] if t is not None)}

Initial state hints: {json.dumps(spec.state, indent=2)[:300]}

Generate a compelling 2-4 paragraph world background:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.provider.chat(messages)
            background = response.content.strip()

            # Clean up any markdown or formatting
            if background.startswith("```") or background.endswith("```"):
                background = background.replace("```", "").strip()

            return background
        except Exception as e:
            logger.error(f"World background generation failed: {e}")
            return f"Welcome to {spec.name}. Your adventure begins in a world full of mystery and challenge."

    async def _generate_entity_backgrounds(
        self,
        entities: List[Dict[str, Any]],
        spec: ScenarioSpec,
        world_background: str,
        max_entities: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Generate detailed backgrounds for each entity.

        Args:
            entities: List of entity dictionaries from the scenario
            spec: The scenario specification for context
            world_background: Generated world background for consistency
            max_entities: Maximum number of entity backgrounds to generate

        Returns:
            List of entities with added 'background' field

        Note:
            If background generation fails for an entity, it keeps the original
            entity data without a background field. Limits generation to max_entities
            for performance.
        """
        if not entities:
            logger.debug("No entities to generate backgrounds for")
            return []

        detailed_entities = []

        # If we need more entities than provided, generate placeholder entities
        entities_to_process = entities[:]
        if max_entities > len(entities):
            logger.debug(
                f"Generating {max_entities - len(entities)} additional placeholder entities"
            )
            for i in range(len(entities), max_entities):
                placeholder_entity = {
                    "id": f"character_{i+1}",
                    "type": "character",
                    "name": f"Character {i+1}",
                }
                entities_to_process.append(placeholder_entity)

        # Generate backgrounds for all entities up to max_entities
        batch_size = min(len(entities_to_process), max_entities)
        entities_to_process = entities_to_process[:batch_size]  # type: ignore

        logger.debug(
            f"Processing {len(entities_to_process)} entities (limit: {max_entities})"
        )

        for entity in entities_to_process:
            try:
                background = await self._generate_single_entity_background(
                    entity, spec, world_background
                )

                # Add background to entity
                entity_with_background = entity.copy()
                entity_with_background["background"] = background
                detailed_entities.append(entity_with_background)

            except Exception as e:
                logger.warning(
                    f"Failed to generate background for entity {entity.get('id')}: {e}"
                )
                # Keep entity without background
                detailed_entities.append(entity)

        return detailed_entities

    async def _generate_single_entity_background(
        self, entity: Dict[str, Any], spec: ScenarioSpec, world_background: str
    ) -> str:
        """
        Generate background for a single entity.

        Args:
            entity: Entity dictionary
            spec: Scenario specification
            world_background: World background for context

        Returns:
            A 1-2 paragraph background for the entity
        """
        system_prompt = """You are a character background writer. Create concise, vivid backgrounds
for characters/entities in interactive stories. Write 1-2 paragraphs covering:
- Who they are
- Their role/position
- Key personality traits or motivations
- How they fit into the world

Be specific and interesting. No meta-commentary."""

        entity_info = {
            "id": entity.get("id", "unknown"),
            "type": entity.get("type", "character"),
            "name": entity.get("name", entity.get("id", "Unknown")),
        }

        user_prompt = f"""Create a background for this entity:

ID: {entity_info['id']}
Type: {entity_info['type']}
Name: {entity_info['name']}

World Context:
{world_background[:500]}...

Scenario: {spec.name}

Generate a compelling 1-2 paragraph background:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.provider.chat(messages)
        background = response.content.strip()

        # Clean up formatting
        if background.startswith("```") or background.endswith("```"):
            background = background.replace("```", "").strip()

        return background

    def _extract_themes(self, spec: ScenarioSpec) -> List[str]:
        """
        Extract thematic elements from the scenario.

        Args:
            spec: The scenario specification

        Returns:
            List of theme keywords extracted from the scenario

        Note:
            This uses simple keyword extraction from scenario name,
            action IDs, and loss condition messages.
        """
        themes = []

        # Extract from name
        name_words = spec.name.lower().split()
        themes.extend([w for w in name_words if len(w) > 4])

        # Extract from action IDs (look for thematic words)
        action_themes = set()
        for action in spec.actions[:10]:
            words = action.id.replace("_", " ").split()
            action_themes.update([w for w in words if len(w) > 4])
        themes.extend(list(action_themes)[:5])

        # Extract from loss conditions
        for condition in spec.loss_conditions[:3]:
            message_words = condition.message.lower().split()
            themes.extend([w for w in message_words if len(w) > 5])

        # Return unique themes, limit to 5
        return list(set(themes))[:5]
