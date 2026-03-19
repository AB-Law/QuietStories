"""
NPC Engine — runs autonomous NPC decision loops each turn.

Two kinds of NPC turns:
  In-scene   NPCs at the same location as the player act every turn, sequentially,
             so each one sees what the previous did.
  Off-scene  NPCs elsewhere act every N turns (config: npc_offscene_interval),
             catching up on N turns of activity in one call.

NPC decisions are first-person: the LLM plays the character from their POV,
knowing only what they would know — their memories, their observations, their goals.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain.schema import HumanMessage, SystemMessage

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.engine.context_builder import ContextBuilder
from backend.engine.narrator import _compute_op, _extract_json
from backend.prompts import (
    NPC_DECISION_SYSTEM,
    NPC_DECISION_USER,
    NPC_INSCENE_NOTE,
    NPC_OFFSCENE_NOTE,
)
from backend.schemas.outcome import StateChange, VisibleDialogue
from backend.schemas.turn import MemoryEntry, NPCAction, NPCDecision, OffSceneNPCDecision
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 1


class NPCEngine:
    """Runs the NPC decision loop for one game turn."""

    def __init__(self, db: DatabaseManager, provider: Any):
        self.db = db
        self.provider = provider
        self.context_builder = ContextBuilder(db)

    async def run_npc_turns(
        self, session_id: str, current_turn: int
    ) -> List[NPCDecision | OffSceneNPCDecision]:
        """
        Run all active NPCs for the current turn.

        In-scene NPCs run sequentially (each sees the previous one's action).
        Off-scene NPCs run every npc_offscene_interval turns.

        Returns the list of decisions for logging and turn output.
        """
        player = self.db.get_player_actor(session_id)
        if not player:
            return []

        all_actors = self.db.get_all_actors(session_id)
        npcs = [a for a in all_actors if not a["is_player"]]

        in_scene = [a for a in npcs if a["location_id"] == player["location_id"]]
        off_scene = [a for a in npcs if a["location_id"] != player["location_id"]]

        decisions: List[NPCDecision | OffSceneNPCDecision] = []

        # In-scene: sequential so each NPC sees the previous one's action
        for npc in in_scene:
            decision = await self._run_inscene_npc(session_id, npc, current_turn)
            if decision:
                decisions.append(decision)
                self._apply_npc_state_changes(session_id, decision.state_changes)

        # Off-scene: run on turn 1 and then every npc_offscene_interval turns
        if current_turn == 1 or current_turn % settings.npc_offscene_interval == 0:
            for npc in off_scene:
                decision = await self._run_offscene_npc(
                    session_id, npc, current_turn,
                    turns_elapsed=settings.npc_offscene_interval,
                )
                if decision:
                    decisions.append(decision)
                    self._apply_npc_state_changes(session_id, decision.state_changes)

        return decisions

    # ------------------------------------------------------------------ #
    # In-scene NPC                                                        #
    # ------------------------------------------------------------------ #

    async def _run_inscene_npc(
        self, session_id: str, actor: Dict[str, Any], current_turn: int
    ) -> Optional[NPCDecision]:
        ctx = self.context_builder.build_npc_context(session_id, actor["actor_id"], turns_elapsed=1)
        user_prompt = self._format_npc_prompt(ctx, elapsed_note=NPC_INSCENE_NOTE)

        messages = [
            SystemMessage(content=NPC_DECISION_SYSTEM),
            HumanMessage(content=user_prompt),
        ]

        try:
            data = await self._call_with_retry(messages, actor["actor_id"])
            decision = _parse_npc_decision(actor["actor_id"], data)
            logger.debug(
                f"[NPC] {actor['name']} (turn {current_turn}): "
                f"{decision.action.type if decision.action else 'no action'}"
            )
            return decision
        except Exception as e:
            logger.error(f"[NPC] Failed to get decision for {actor['actor_id']}: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Off-scene NPC                                                       #
    # ------------------------------------------------------------------ #

    async def _run_offscene_npc(
        self, session_id: str, actor: Dict[str, Any],
        current_turn: int, turns_elapsed: int
    ) -> Optional[OffSceneNPCDecision]:
        ctx = self.context_builder.build_npc_context(
            session_id, actor["actor_id"], turns_elapsed=turns_elapsed
        )
        elapsed_note = NPC_OFFSCENE_NOTE.format(turns_elapsed=turns_elapsed)
        user_prompt = self._format_npc_prompt(ctx, elapsed_note=elapsed_note)

        messages = [
            SystemMessage(content=NPC_DECISION_SYSTEM),
            HumanMessage(content=user_prompt),
        ]

        try:
            data = await self._call_with_retry(messages, actor["actor_id"])
            decision = _parse_offscene_decision(actor["actor_id"], turns_elapsed, data)
            logger.debug(
                f"[NPC] {actor['name']} (off-scene, {turns_elapsed} turns): "
                f"{decision.summary[:60]}..."
            )
            return decision
        except Exception as e:
            logger.error(f"[NPC] Failed to get off-scene decision for {actor['actor_id']}: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Prompt formatting                                                   #
    # ------------------------------------------------------------------ #

    def _format_npc_prompt(self, ctx: Dict[str, Any], elapsed_note: str) -> str:
        world_text = ContextBuilder.format_world_block(ctx["world"])
        actor_text = ContextBuilder.format_actor_block(ctx["actor"], pov=True)

        observable_text = "\n".join(
            ContextBuilder.format_actor_block(a, pov=False)
            for a in ctx.get("observable_actors", [])
        ) or "Nobody else is visible."

        local_events = ctx.get("recent_local_events", [])
        events_text = "\n".join(
            f"Turn {e['turn']}: {e['summary']}" for e in local_events
        ) or "Nothing notable has happened recently."

        return NPC_DECISION_USER.format(
            world=world_text,
            actor=actor_text,
            observable_actors=observable_text,
            recent_local_events=events_text,
            elapsed_note=elapsed_note,
        )

    # ------------------------------------------------------------------ #
    # LLM call + retry                                                    #
    # ------------------------------------------------------------------ #

    async def _call_with_retry(
        self, messages: List[Any], actor_id: str
    ) -> Dict[str, Any]:
        last_error: Optional[str] = None

        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0 and last_error:
                messages = messages + [
                    HumanMessage(
                        content=f"Your previous response was not valid JSON. Error: {last_error}\n"
                                f"Return ONLY valid JSON starting with {{ and ending with }}."
                    )
                ]
            try:
                response = await self.provider.chat(messages)
                return _extract_json(response.content)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[NPC:{actor_id}] Attempt {attempt + 1} failed: {e}")

        raise ValueError(f"All retries exhausted for NPC {actor_id}: {last_error}")

    # ------------------------------------------------------------------ #
    # State application                                                   #
    # ------------------------------------------------------------------ #

    def _apply_npc_state_changes(
        self, session_id: str, state_changes: List[StateChange]
    ) -> None:
        if not state_changes:
            return

        session = self.db.get_session(session_id)
        if not session:
            return

        global_state = dict(session.get("global_state", {}))
        world = self.db.get_world_state(session_id) or {}
        locations = dict(world.get("locations", {}))
        factions = dict(world.get("factions", {}))
        actors_cache: Dict[str, Dict[str, Any]] = {}

        from backend.engine.narrator import _apply_single_change
        for change in state_changes:
            try:
                _apply_single_change(
                    change, global_state, locations, factions,
                    actors_cache, session_id, self.db,
                )
            except Exception as e:
                logger.warning(f"[NPC] Failed to apply state change {change}: {e}")

        self.db.update_session(session_id, global_state=global_state)
        if world:
            self.db.save_world_state(
                session_id, locations=locations, factions=factions,
                time_of_day=world.get("time_of_day", "unknown"),
                day=world.get("day", 1),
                active_events=world.get("active_events", []),
            )
        for actor_id, actor_data in actors_cache.items():
            self.db.save_actor(session_id, actor_id, actor_data)


# ------------------------------------------------------------------ #
# Parsing helpers                                                     #
# ------------------------------------------------------------------ #

def _parse_npc_decision(actor_id: str, data: Dict[str, Any]) -> NPCDecision:
    action = None
    raw_action = data.get("action")
    if raw_action and isinstance(raw_action, dict) and raw_action.get("type"):
        action = NPCAction(
            type=raw_action["type"],
            target_id=raw_action.get("target_id"),
            content=raw_action.get("content"),
            visible_to_player=raw_action.get("visible_to_player", True),
        )

    memories = []
    for m in data.get("new_memories", []):
        if isinstance(m, dict) and "content" in m:
            memories.append(MemoryEntry(
                actor_id=m.get("actor_id", actor_id),
                content=m["content"],
                tags=m.get("tags", []),
                visibility=m.get("visibility", "private"),
            ))

    state_changes = []
    for sc in data.get("state_changes", []):
        if isinstance(sc, dict) and "op" in sc and "path" in sc:
            try:
                state_changes.append(StateChange(**sc))
            except Exception:
                pass

    return NPCDecision(
        actor_id=actor_id,
        private_thought=data.get("private_thought", ""),
        action=action,
        new_memories=memories,
        state_changes=state_changes,
    )


def _parse_offscene_decision(
    actor_id: str, turns_elapsed: int, data: Dict[str, Any]
) -> OffSceneNPCDecision:
    # Off-scene uses the same JSON shape as in-scene but wraps into OffSceneNPCDecision
    base = _parse_npc_decision(actor_id, data)
    return OffSceneNPCDecision(
        actor_id=actor_id,
        turns_elapsed=turns_elapsed,
        summary=data.get("private_thought", ""),
        actions=[base.action] if base.action else [],
        new_memories=base.new_memories,
        state_changes=base.state_changes,
    )
