"""
Scenario generator using LLM to create dynamic scenarios from free text
"""

import json
import random
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from backend.prompts import (
    ENTITY_COUNT_GENERATION_SYSTEM,
    ENTITY_COUNT_GENERATION_USER,
    ENTITY_GENERATION_SYSTEM,
    ENTITY_GENERATION_USER,
    SCENARIO_GENERATION_SYSTEM,
    SCENARIO_GENERATION_USER,
    WORLD_BACKGROUND_GENERATION_SYSTEM,
    WORLD_BACKGROUND_GENERATION_USER,
)
from backend.providers.factory import create_provider


class ScenarioGenerator:
    """Generates dynamic scenarios from free-text descriptions"""

    def __init__(self):
        self.provider = create_provider()

    async def generate_scenario(self, description: str) -> Dict[str, Any]:
        """Generate world background and entities for a scenario"""

        import logging

        logger = logging.getLogger(__name__)

        logger.info("Starting simplified scenario generation...")

        # Step 1: Generate world background
        logger.info("Step 1: Generating world background...")
        world_background = await self._generate_world_background(description)
        logger.info(f"✓ World background generated ({len(world_background)} chars)")

        # Step 2: Determine entity count
        logger.info("Step 2: Determining entity count...")
        entity_count = await self._determine_entity_count(description, world_background)
        logger.info(f"✓ Will generate {entity_count} entities")

        # Step 3: Generate entities in batches
        logger.info("Step 3: Generating entities in batches...")
        entities = await self._generate_entities_parallel(
            description, world_background, entity_count
        )
        logger.info(f"✓ Generated {len(entities)} entities")

        # Return simplified scenario data
        scenario_data = {
            "description": description,
            "world_background": world_background,
            "entities": entities,
            "generated_at": "2025-01-01T00:00:00Z",  # Placeholder
        }

        logger.info("✓ Scenario generation completed")
        return scenario_data

    async def _generate_world_background(self, description: str) -> str:
        """Generate world background using LLM"""

        messages = [
            SystemMessage(content=WORLD_BACKGROUND_GENERATION_SYSTEM),
            HumanMessage(
                content=WORLD_BACKGROUND_GENERATION_USER.format(description=description)
            ),
        ]

        response = await self.provider.chat(messages)
        return response.content.strip()

    async def _determine_entity_count(
        self, description: str, world_background: str
    ) -> int:
        """Determine optimal entity count using LLM"""

        import json

        messages = [
            SystemMessage(content=ENTITY_COUNT_GENERATION_SYSTEM),
            HumanMessage(
                content=ENTITY_COUNT_GENERATION_USER.format(
                    description=description, world_background=world_background
                )
            ),
        ]

        response = await self.provider.chat(messages)
        content = response.content.strip()

        # Extract JSON
        try:
            data = json.loads(content)
            count = data.get("entity_count", 8)  # Default to 8 if not found
            return max(5, min(12, count))  # Clamp between 5-12
        except json.JSONDecodeError:
            # Fallback: try to extract number from text
            import re

            match = re.search(r"(\d+)", content)
            if match:
                count = int(match.group(1))
                return max(5, min(12, count))
            return 8  # Default fallback

    async def _generate_entities_parallel(
        self, description: str, world_background: str, count: int
    ) -> List[Dict[str, Any]]:
        """Generate entities in batches using multiple LLM calls"""

        import asyncio
        import math

        # Calculate number of batches needed (3-5 entities per batch)
        batch_size = 4  # Target 4 entities per batch
        num_batches = math.ceil(count / batch_size)

        async def generate_entity_batch(
            batch_index: int, existing_entities: List[Dict[str, Any]]
        ) -> List[Dict[str, Any]]:
            """Generate a batch of entities"""

            existing_summary = (
                "\n".join(
                    [
                        f"- {e.get('name', e.get('id', 'Unknown'))} ({e.get('type', 'unknown')}): {e.get('background', '')[:100]}..."
                        for e in existing_entities
                    ]
                )
                if existing_entities
                else "None yet"
            )

            # Calculate how many entities to request for this batch
            remaining_needed = count - len(existing_entities)
            entities_to_generate = min(batch_size, remaining_needed)

            # Create the prompt with the specific count
            user_prompt = ENTITY_GENERATION_USER.format(
                description=description,
                world_background=world_background,
                existing_entities=existing_summary,
            ).replace("3-5", f"{entities_to_generate}")

            messages = [
                SystemMessage(content=ENTITY_GENERATION_SYSTEM),
                HumanMessage(content=user_prompt),
            ]

            response = await self.provider.chat(messages)
            content = response.content.strip()

            # Extract JSON array
            try:
                # Try to find JSON array in response
                start_idx = content.find("[")
                end_idx = content.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    entity_batch = json.loads(json_str)
                    if isinstance(entity_batch, list):
                        return entity_batch
                    else:
                        raise json.JSONDecodeError("Expected array", content, 0)
                else:
                    raise json.JSONDecodeError("No JSON array found", content, 0)
            except json.JSONDecodeError as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse entity batch {batch_index}: {e}")
                # Fallback: create basic entities
                return [
                    {
                        "id": f"fallback_entity_{len(existing_entities) + i + 1}",
                        "type": "character",
                        "name": f"Fallback Character {len(existing_entities) + i + 1}",
                        "background": f"A mysterious figure in this world. (Generated as fallback due to parsing error)",
                    }
                    for i in range(
                        min(entities_to_generate, 3)
                    )  # Generate up to 3 fallback entities
                ]

        # Generate batches sequentially to maintain context of existing entities
        all_entities: List[Dict[str, Any]] = []
        for batch_index in range(num_batches):
            batch = await generate_entity_batch(batch_index, all_entities)
            all_entities.extend(batch)

            # Stop if we have enough entities
            if len(all_entities) >= count:
                break

        # Trim to exact count requested
        return all_entities[:count]
