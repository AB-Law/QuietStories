"""
Session initializer — converts a ScenarioSpec into a live session in the DB.

Steps:
  1. Create the session record
  2. Persist world state (Tier 1) from spec.world
  3. Persist each actor (Tier 2) from spec.actors
  4. Seed memory log (Tier 3) from each actor's seed_memories
  5. Generate and store the opening narrative
"""

from typing import Any, Optional

from langchain.schema import HumanMessage, SystemMessage

from backend.db.manager import DatabaseManager
from backend.providers.base import BaseProvider
from backend.schemas.scenario import ScenarioSpec
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SessionInitializer:
    """Converts a ScenarioSpec into a fully initialized session."""

    def __init__(self, db: DatabaseManager, provider: BaseProvider):
        self.db = db
        self.provider = provider

    async def initialize(
        self,
        spec: ScenarioSpec,
        scenario_db_id: str,
        player_name: Optional[str] = None,
    ) -> str:
        """
        Create a new session from a ScenarioSpec and return the session_id.

        Args:
            spec:        The scenario to initialize.
            player_name: Optional override for the player character's name.

        Returns:
            The new session ID.
        """
        logger.info(f"Initializing session for scenario: {spec.name}")

        # 1. Create session — use the DB UUID, not spec.id
        session_id = self.db.create_session(
            scenario_id=scenario_db_id,
            global_state=dict(spec.global_state),
        )

        # 2. Persist world state
        locations = {
            loc.id: {
                "name": loc.name,
                "description": loc.description,
                "connected_to": loc.connected_to,
                "state": dict(loc.state),
            }
            for loc in spec.world.locations
        }
        factions = {
            fac.id: {
                "name": fac.name,
                "description": fac.description,
                "disposition": fac.disposition,
            }
            for fac in spec.world.factions
        }
        self.db.save_world_state(
            session_id=session_id,
            locations=locations,
            factions=factions,
            time_of_day=spec.world.initial_time,
            day=spec.world.initial_day,
            active_events=[],
        )
        logger.debug(
            f"[Init] World state saved: {len(locations)} locations, {len(factions)} factions"
        )

        # 3 + 4. Persist actors and seed their memories
        for actor in spec.actors:
            name = player_name if (actor.is_player and player_name) else actor.name

            self.db.save_actor(
                session_id=session_id,
                actor_id=actor.id,
                data={
                    "name": name,
                    "is_player": actor.is_player,
                    "personality": actor.personality,
                    "background": actor.background,
                    "location_id": actor.location_id,
                    "state": dict(actor.state),
                    "goals": [g.model_dump() for g in actor.goals],
                    "relationships": [r.model_dump() for r in actor.relationships],
                    "known_facts": list(actor.known_facts),
                    "last_action_turn": 0,
                },
            )

            # Seed memories into the memory log at turn 0
            for mem in actor.seed_memories:
                self.db.add_memory(
                    session_id=session_id,
                    actor_id=actor.id,
                    turn=0,
                    content=mem.content,
                    tags=mem.tags,
                    visibility=mem.visibility,
                )

            role = "player" if actor.is_player else "NPC"
            logger.debug(
                f"[Init] {role} '{name}' saved with {len(actor.seed_memories)} seed memories"
            )

        # 5. Generate opening narrative and store as turn 0
        opening = await self._generate_opening(spec)
        self.db.append_turn(
            session_id=session_id,
            turn=0,
            player_action="[session start]",
            narrator_output={"narrative": opening, "state_changes": [], "visible_dialogue": []},
            npc_decisions=[],
            roll_results=[],
        )

        logger.info(f"Session {session_id} initialized successfully")
        return session_id

    async def _generate_opening(self, spec: ScenarioSpec) -> str:
        """
        Generate the opening narrative for the session.

        This is the first text the player sees — it sets the scene, establishes
        tone, and places the player character in the world.
        """
        player = next((a for a in spec.actors if a.is_player), None)
        player_info = ""
        if player:
            player_info = (
                f"Player character: {player.name}\n"
                f"Background: {player.background}\n"
                f"Starting location: {player.location_id}"
            )

        npc_names = [a.name for a in spec.actors if not a.is_player]

        system = (
            "You write immersive opening scenes for interactive stories. "
            "Set the scene vividly in 3-4 paragraphs. Establish the world, the atmosphere, "
            "and the player character's immediate situation. Hint at tensions and possibilities "
            "without resolving anything. End with the player character poised to act."
        )
        user = (
            f"Scenario: {spec.name}\n"
            f"World: {spec.world.description}\n"
            f"Tone: {spec.world.tone}\n"
            f"{player_info}\n"
            f"Other characters present in this world: {', '.join(npc_names)}\n\n"
            f"Write the opening scene:"
        )

        try:
            response = await self.provider.chat(
                [SystemMessage(content=system), HumanMessage(content=user)]
            )
            return response.content.strip()
        except Exception as e:
            logger.error(f"[Init] Opening generation failed: {e}")
            return (
                f"Welcome to {spec.name}. {spec.world.description} "
                f"Your story begins now."
            )
