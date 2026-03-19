"""
Narrator — resolves the player's action and produces a structured story response.

One public method: resolve_turn()
  1. Build context from the three memory tiers via ContextBuilder
  2. Format into narrator prompt
  3. Call LLM
  4. Parse JSON response into NarratorOutput
  5. Apply state changes to DB
  6. Return NarratorOutput for the turn engine to use
"""

import json
import re
from typing import Any, Dict, List, Optional

from langchain.schema import HumanMessage, SystemMessage

from backend.db.manager import DatabaseManager
from backend.engine.context_builder import ContextBuilder
from backend.prompts import NARRATOR_SYSTEM, NARRATOR_USER
from backend.schemas.turn import MemoryEntry, NarratorOutput
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Max times to retry a malformed JSON response before giving up
_MAX_RETRIES = 2


class Narrator:
    """Resolves player actions into story narrative and state changes."""

    def __init__(self, db: DatabaseManager, provider: Any):
        self.db = db
        self.provider = provider
        self.context_builder = ContextBuilder(db)

    async def resolve_turn(self, session_id: str, player_action: str) -> NarratorOutput:
        """
        Run the narrator for one player turn.

        Builds context, calls LLM, parses and validates the response,
        applies state changes to the DB, and returns the NarratorOutput.
        """
        ctx = self.context_builder.build_narrator_context(session_id, player_action)

        world_text = ContextBuilder.format_world_block(ctx["world"])
        player_text = ContextBuilder.format_actor_block(ctx["player"], pov=True)
        npcs_text = "\n\n".join(
            ContextBuilder.format_actor_block(npc, pov=False)
            for npc in ctx["in_scene_npcs"]
        ) or "No other characters are present."
        history_text = ContextBuilder.format_turn_history(ctx["recent_turns"])

        user_prompt = NARRATOR_USER.format(
            world=world_text,
            player=player_text,
            npcs=npcs_text,
            recent_turns=history_text,
            player_action=player_action,
        )

        messages = [
            SystemMessage(content=NARRATOR_SYSTEM),
            HumanMessage(content=user_prompt),
        ]

        output = await self._call_with_retry(messages)
        self._apply_state_changes(session_id, output.state_changes)
        return output

    # ------------------------------------------------------------------ #
    # LLM call + JSON parsing                                             #
    # ------------------------------------------------------------------ #

    async def _call_with_retry(self, messages: List[Any]) -> NarratorOutput:
        last_error: Optional[str] = None

        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0 and last_error:
                # Append the error so the LLM can self-correct
                messages = messages + [
                    HumanMessage(
                        content=f"Your previous response was not valid JSON. Error: {last_error}\n"
                                f"Return ONLY valid JSON starting with {{ and ending with }}."
                    )
                ]

            try:
                response = await self.provider.chat(messages)
                raw = response.content
                data = _extract_json(raw)
                return _parse_narrator_output(data)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[Narrator] Attempt {attempt + 1} failed: {e}")

        # All retries exhausted — return a safe fallback
        logger.error("[Narrator] All retries failed, returning fallback response")
        return NarratorOutput(
            narrative=(
                "Something stirs in the silence, but the moment passes without resolution. "
                "The world holds its breath, waiting for your next move."
            ),
            state_changes=[],
            suggested_actions=["Look around", "Wait and observe", "Move to another location"],
        )

    # ------------------------------------------------------------------ #
    # State application                                                   #
    # ------------------------------------------------------------------ #

    def _apply_state_changes(self, session_id: str, state_changes: List[Any]) -> None:
        """
        Apply state_changes from the narrator to the DB.

        Path conventions (dot notation):
          actor.{actor_id}.state.{field}    → actor state dict
          actor.{actor_id}.location_id      → actor location
          actor.{actor_id}.goals            → actor goals list
          world.locations.{loc_id}.state.{field} → location state
          world.factions.{faction_id}.disposition → faction disposition
          global_state.{field}              → session global state
        """
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

        for change in state_changes:
            try:
                _apply_single_change(
                    change, global_state, locations, factions, actors_cache,
                    session_id, self.db,
                )
            except Exception as e:
                logger.warning(f"[Narrator] Failed to apply state change {change}: {e}")

        # Flush everything back to DB
        self.db.update_session(session_id, global_state=global_state)
        if world:
            self.db.save_world_state(
                session_id,
                locations=locations,
                factions=factions,
                time_of_day=world.get("time_of_day", "unknown"),
                day=world.get("day", 1),
                active_events=world.get("active_events", []),
            )
        for actor_id, actor_data in actors_cache.items():
            self.db.save_actor(session_id, actor_id, actor_data)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _apply_single_change(
    change: Any,
    global_state: Dict[str, Any],
    locations: Dict[str, Any],
    factions: Dict[str, Any],
    actors_cache: Dict[str, Dict[str, Any]],
    session_id: str,
    db: DatabaseManager,
) -> None:
    op = change.op
    path = change.path
    value = change.value
    parts = path.split(".")

    if parts[0] == "global_state" and len(parts) >= 2:
        field = ".".join(parts[1:])
        _mutate(global_state, field.split("."), op, value)

    elif parts[0] == "actor" and len(parts) >= 3:
        actor_id = parts[1]
        if actor_id not in actors_cache:
            actor = db.get_actor(session_id, actor_id)
            if not actor:
                # Try case-insensitive fallback (LLM sometimes uses name instead of id)
                all_actors = db.get_all_actors(session_id)
                actor = next(
                    (a for a in all_actors
                     if a["actor_id"].lower() == actor_id.lower()),
                    None,
                )
                if actor:
                    actor_id = actor["actor_id"]  # use canonical id going forward
                else:
                    logger.debug(f"[Narrator] Actor '{actor_id}' not found, skipping change")
                    return
            actors_cache[actor_id] = actor

        sub_path = parts[2:]
        if sub_path[0] == "state":
            _mutate(actors_cache[actor_id]["state"], sub_path[1:], op, value)
        elif sub_path[0] == "location_id":
            actors_cache[actor_id]["location_id"] = value
        elif sub_path[0] == "goals":
            _mutate_list(actors_cache[actor_id], "goals", sub_path, op, value)
        elif sub_path[0] == "relationships":
            _mutate_list(actors_cache[actor_id], "relationships", sub_path, op, value)

    elif parts[0] == "world" and len(parts) >= 4:
        if parts[1] == "locations" and parts[3] == "state" and len(parts) >= 5:
            loc_id = parts[2]
            if loc_id in locations:
                _mutate(locations[loc_id].setdefault("state", {}), parts[4:], op, value)
        elif parts[1] == "factions" and parts[3] == "disposition":
            fac_id = parts[2]
            if fac_id in factions:
                factions[fac_id]["disposition"] = _compute_op(
                    factions[fac_id].get("disposition", 0.0), op, value
                )


def _mutate(target: Dict[str, Any], path_parts: List[str], op: str, value: Any) -> None:
    """Drill into a dict and apply an op at the leaf."""
    if not path_parts:
        return
    for part in path_parts[:-1]:
        target = target.setdefault(part, {})
    leaf = path_parts[-1]
    current = target.get(leaf)
    target[leaf] = _compute_op(current, op, value)


def _mutate_list(actor: Dict[str, Any], list_key: str, sub_path: List[str],
                 op: str, value: Any) -> None:
    """Handle push/pop/set on actor list fields (goals, relationships)."""
    lst = actor.get(list_key, [])
    if op == "push":
        lst.append(value)
    elif op == "pop" and lst:
        lst.pop()
    elif op == "set":
        actor[list_key] = value
        return
    actor[list_key] = lst


def _compute_op(current: Any, op: str, value: Any) -> Any:
    if op == "set":
        return value
    if op == "inc":
        return (current or 0) + value
    if op == "dec":
        return (current or 0) - value
    if op == "mul":
        return (current or 0) * value
    if op == "patch" and isinstance(current, dict) and isinstance(value, dict):
        return {**current, **value}
    if op == "push":
        lst = list(current) if isinstance(current, list) else []
        lst.append(value)
        return lst
    if op == "pop":
        lst = list(current) if isinstance(current, list) else []
        if lst:
            lst.pop()
        return lst
    if op == "addlog":
        lst = list(current) if isinstance(current, list) else []
        lst.append(value)
        return lst
    return current


def _extract_json(raw: str) -> Dict[str, Any]:
    """Extract a JSON object from raw LLM output, stripping markdown fences."""
    raw = raw.strip()
    # Strip ```json ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()
    # Find the outermost { ... }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {raw[:200]}")
    return json.loads(raw[start : end + 1])


def _parse_narrator_output(data: Dict[str, Any]) -> NarratorOutput:
    """Parse raw dict into NarratorOutput, tolerating missing optional fields."""
    # Coerce state_changes entries
    state_changes = []
    for sc in data.get("state_changes", []):
        if isinstance(sc, dict) and "op" in sc and "path" in sc:
            from backend.schemas.outcome import StateChange
            try:
                state_changes.append(StateChange(**sc))
            except Exception as e:
                logger.warning(f"[Narrator] Skipping invalid state_change {sc}: {e}")

    # Coerce memories
    memories = []
    for m in data.get("new_memories", []):
        if isinstance(m, dict) and "actor_id" in m and "content" in m:
            memories.append(MemoryEntry(
                actor_id=m["actor_id"],
                content=m["content"],
                tags=m.get("tags", []),
                visibility=m.get("visibility", "private"),
            ))

    # Coerce dialogue
    from backend.schemas.outcome import RollRequest, VisibleDialogue
    dialogue = []
    for d in data.get("visible_dialogue", []):
        if isinstance(d, dict) and "entity_id" in d and "utterance" in d:
            dialogue.append(VisibleDialogue(**d))

    # Coerce roll requests
    rolls = []
    for r in data.get("roll_requests", []):
        if isinstance(r, dict) and "kind" in r and "difficulty" in r:
            try:
                rolls.append(RollRequest(**r))
            except Exception:
                pass

    return NarratorOutput(
        narrative=data.get("narrative", ""),
        visible_dialogue=dialogue,
        state_changes=state_changes,
        new_memories=memories,
        roll_requests=rolls,
        suggested_actions=data.get("suggested_actions", []),
    )
