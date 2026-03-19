"""
Context builder — assembles the prompt context for each LLM call.

Every LLM call (narrator or NPC decision) gets a context assembled from
the three memory tiers:

  Tier 1 — World state     Always present. Locations, factions, time.
  Tier 2 — Actor card      Always present for active actors. Identity, goals,
                           relationships, known_facts.
  Tier 3 — Memory log      Retrieved selectively. Recent entries + tag-matched
                           entries for the current scene.

The output is plain text/dict structures ready to be inserted into prompts.
No LLM calls happen here — this is pure data assembly.
"""

from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.db.manager import DatabaseManager


class ContextBuilder:
    """Assembles prompt context from the three memory tiers."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def build_narrator_context(self, session_id: str, player_action: str) -> Dict[str, Any]:
        """
        Build context for the narrator LLM.

        The narrator sees:
          - World state (Tier 1)
          - Player's actor card + retrieved memories (Tier 2 + 3)
          - Cards for all in-scene NPCs (those sharing the player's location)
          - Recent turn history (last N turns)
          - The player's action
        """
        session = self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_turn = session["turn"]
        world = self._build_world_block(session_id)
        player = self.db.get_player_actor(session_id)
        if not player:
            raise ValueError(f"No player actor found for session {session_id}")

        in_scene_npcs = [
            a for a in self.db.get_actors_at_location(session_id, player["location_id"])
            if not a["is_player"]
        ]

        player_block = self._build_actor_block(
            session_id, player, current_turn, is_pov=True
        )
        npc_blocks = [
            self._build_actor_block(session_id, npc, current_turn, is_pov=False)
            for npc in in_scene_npcs
        ]
        recent_turns = self._build_turn_history(session_id)

        return {
            "world": world,
            "player": player_block,
            "in_scene_npcs": npc_blocks,
            "recent_turns": recent_turns,
            "current_turn": current_turn,
            "player_action": player_action,
        }

    def build_npc_context(self, session_id: str, actor_id: str,
                          turns_elapsed: int = 1) -> Dict[str, Any]:
        """
        Build context for an NPC decision LLM call.

        The NPC sees only what they would know:
          - Their own actor card + retrieved memories (their POV)
          - The current world state
          - Actors they can observe (same location only)
          - What just happened in their location (last turn's narrator output,
            if they were present — otherwise nothing)
          - How many turns have passed (for off-scene NPCs)
        """
        session = self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_turn = session["turn"]
        actor = self.db.get_actor(session_id, actor_id)
        if not actor:
            raise ValueError(f"Actor {actor_id} not found in session {session_id}")

        world = self._build_world_block(session_id)
        actor_block = self._build_actor_block(
            session_id, actor, current_turn, is_pov=True
        )

        # What can this NPC observe right now?
        observable_actors = [
            self._build_actor_public_summary(a)
            for a in self.db.get_actors_at_location(session_id, actor["location_id"])
            if a["actor_id"] != actor_id
        ]

        # What happened in their location recently (limited to what they'd witness)
        recent_local_events = self._build_local_events(
            session_id, actor["location_id"], limit=3
        )

        return {
            "world": world,
            "actor": actor_block,
            "observable_actors": observable_actors,
            "recent_local_events": recent_local_events,
            "current_turn": current_turn,
            "turns_elapsed": turns_elapsed,
        }

    # ------------------------------------------------------------------ #
    # Tier 1 — World block                                                #
    # ------------------------------------------------------------------ #

    def _build_world_block(self, session_id: str) -> Dict[str, Any]:
        world = self.db.get_world_state(session_id)
        if not world:
            return {}
        return {
            "time_of_day": world["time_of_day"],
            "day": world["day"],
            "locations": world["locations"],
            "factions": world["factions"],
            "active_events": world["active_events"],
        }

    # ------------------------------------------------------------------ #
    # Tier 2 + 3 — Actor block                                            #
    # ------------------------------------------------------------------ #

    def _build_actor_block(self, session_id: str, actor: Dict[str, Any],
                           current_turn: int, is_pov: bool) -> Dict[str, Any]:
        """
        Build the full context block for an actor.

        is_pov=True: this actor is the one making the decision (narrator POV = player).
        is_pov=False: this is an observed NPC — show only public-facing info.
        """
        if not is_pov:
            return self._build_actor_public_summary(actor)

        # Retrieve Tier 3 memories
        memories = self._retrieve_memories(session_id, actor, current_turn)

        # Active goals only
        active_goals = [
            g for g in (actor["goals"] or [])
            if g.get("status") == "active"
        ]

        # Enrich relationships with display names so actor_ids don't leak into prompts
        enriched_relationships = []
        for rel in (actor["relationships"] or []):
            enriched = dict(rel)
            other = self.db.get_actor(session_id, rel.get("actor_id", ""))
            if other:
                enriched["name"] = other["name"]
            enriched_relationships.append(enriched)

        return {
            "actor_id": actor["actor_id"],
            "name": actor["name"],
            "personality": actor["personality"],
            "background": actor["background"],
            "location_id": actor["location_id"],
            "state": actor["state"],
            "active_goals": active_goals,
            "relationships": enriched_relationships,
            "known_facts": actor["known_facts"],   # Tier 2 — always included
            "retrieved_memories": memories,         # Tier 3 — selectively retrieved
        }

    def _build_actor_public_summary(self, actor: Dict[str, Any]) -> Dict[str, Any]:
        """
        What other actors can observe about this actor.
        No private goals, no memories, no internal state beyond appearance.
        """
        public_goals = [
            g for g in (actor["goals"] or [])
            if not g.get("private", True) and g.get("status") == "active"
        ]
        return {
            "actor_id": actor["actor_id"],
            "name": actor["name"],
            "location_id": actor["location_id"],
            "public_goals": public_goals,
            # Surface-level state only — e.g. mood or health if the spec puts them here
            "visible_state": {
                k: v for k, v in (actor["state"] or {}).items()
                if k in ("mood", "health", "appearance", "stance")
            },
        }

    # ------------------------------------------------------------------ #
    # Tier 3 — Memory retrieval                                           #
    # ------------------------------------------------------------------ #

    def _retrieve_memories(self, session_id: str, actor: Dict[str, Any],
                           current_turn: int) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for an actor for this turn.

        Strategy:
          1. Always include the N most recent memories.
          2. Build a tag set from the current scene (location + co-present actors).
          3. Pull tag-matched memories, deduplicating against the recency set.
        """
        recent = self.db.get_recent_memories(
            session_id, actor["actor_id"],
            limit=settings.memory_retrieval_recent,
        )
        recent_ids = {m["id"] for m in recent}

        # Scene tags: current location + actor IDs in the same location
        scene_tags = [actor["location_id"]]
        co_present = self.db.get_actors_at_location(session_id, actor["location_id"])
        scene_tags += [a["actor_id"] for a in co_present if a["actor_id"] != actor["actor_id"]]

        tagged = self.db.get_tagged_memories(
            session_id, actor["actor_id"], scene_tags,
            limit=settings.memory_retrieval_tagged,
        )
        tagged_deduped = [m for m in tagged if m["id"] not in recent_ids]

        # Recent first, then tagged (older but relevant)
        return recent + tagged_deduped

    # ------------------------------------------------------------------ #
    # Turn history                                                        #
    # ------------------------------------------------------------------ #

    def _build_turn_history(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Return a compact version of the last N turns for the narrator.
        Strips internal NPC thoughts — only what was narrated + visible actions.
        """
        turns = self.db.get_recent_turns(session_id, limit=limit)
        history = []
        for t in turns:
            narrator = t.get("narrator_output", {})
            visible_npc_actions = []
            for dec in t.get("npc_decisions", []):
                action = dec.get("action")
                if action and action.get("visible_to_player", True):
                    visible_npc_actions.append({
                        "actor_id": dec.get("actor_id"),
                        "action": action,
                    })
            history.append({
                "turn": t["turn"],
                "player_action": t["player_action"],
                "narrative": narrator.get("narrative", ""),
                "visible_dialogue": narrator.get("visible_dialogue", []),
                "npc_actions": visible_npc_actions,
            })
        return history

    def _build_local_events(self, session_id: str, location_id: str,
                            limit: int = 3) -> List[Dict[str, Any]]:
        """
        Recent events that occurred at a specific location.
        Used to give NPCs awareness of what happened near them.
        """
        turns = self.db.get_recent_turns(session_id, limit=limit * 2)
        local_events = []
        for t in turns:
            narrator = t.get("narrator_output", {})
            # Include this turn if the player was at this location
            # (We track player location changes through state_changes in the turn log)
            local_events.append({
                "turn": t["turn"],
                "summary": narrator.get("narrative", "")[:300],  # truncated for NPC context
            })
            if len(local_events) >= limit:
                break
        return local_events

    # ------------------------------------------------------------------ #
    # Formatting helpers (used by prompts.py to render context as text)  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_world_block(world: Dict[str, Any]) -> str:
        if not world:
            return "World state unavailable."
        lines = [f"Day {world.get('day', 1)}, {world.get('time_of_day', 'unknown time')}"]

        locations = world.get("locations", {})
        if locations:
            lines.append("\nLocations:")
            for loc_id, loc in locations.items():
                status = loc.get("state", {})
                status_str = f" [{', '.join(f'{k}: {v}' for k, v in status.items())}]" if status else ""
                lines.append(f"  {loc.get('name', loc_id)}: {loc.get('description', '')}{status_str}")

        factions = world.get("factions", {})
        if factions:
            lines.append("\nFactions:")
            for fac_id, fac in factions.items():
                disp = fac.get("disposition", 0.0)
                disp_label = "allied" if disp > 0.3 else ("hostile" if disp < -0.3 else "neutral")
                lines.append(f"  {fac.get('name', fac_id)}: {fac.get('description', '')} (disposition: {disp_label})")

        events = world.get("active_events", [])
        if events:
            lines.append("\nActive events:")
            for ev in events:
                lines.append(f"  - {ev.get('description', str(ev))}")

        return "\n".join(lines)

    @staticmethod
    def format_actor_block(actor_block: Dict[str, Any], pov: bool = True) -> str:
        if not pov:
            name = actor_block.get("name", "Unknown")
            visible = actor_block.get("visible_state", {})
            visible_str = ", ".join(f"{k}: {v}" for k, v in visible.items()) if visible else "nothing notable"
            goals = actor_block.get("public_goals", [])
            goal_str = "; ".join(g.get("description", "") for g in goals) if goals else ""
            result = f"{name} (at {actor_block.get('location_id', '?')}): {visible_str}"
            if goal_str:
                result += f"\n  Apparent goal: {goal_str}"
            return result

        lines = [
            f"Name: {actor_block.get('name')}",
            f"Location: {actor_block.get('location_id')}",
            f"Personality: {actor_block.get('personality')}",
            f"Background: {actor_block.get('background')}",
        ]

        state = actor_block.get("state", {})
        if state:
            lines.append("State: " + ", ".join(f"{k}: {v}" for k, v in state.items()))

        goals = actor_block.get("active_goals", [])
        if goals:
            lines.append("Active goals:")
            for g in goals:
                priority = g.get("priority", "medium")
                lines.append(f"  [{priority}] {g.get('description', '')}")

        relationships = actor_block.get("relationships", [])
        if relationships:
            lines.append("Relationships:")
            for r in relationships:
                score = r.get("score", 0.0)
                label = "trusts" if score > 0.3 else ("distrusts" if score < -0.3 else "is neutral toward")
                other_name = r.get("name") or r.get("actor_id", "unknown")
                lines.append(f"  {label} {other_name}: {r.get('summary', '')}")

        known_facts = actor_block.get("known_facts", [])
        if known_facts:
            lines.append("What they know:")
            for fact in known_facts:
                lines.append(f"  - {fact}")

        memories = actor_block.get("retrieved_memories", [])
        if memories:
            lines.append("Recent memories:")
            for m in memories:
                lines.append(f"  [turn {m.get('turn', '?')}] {m.get('content', '')}")

        return "\n".join(lines)

    @staticmethod
    def format_turn_history(turns: List[Dict[str, Any]]) -> str:
        if not turns:
            return "No prior turns."
        lines = []
        for t in turns:
            lines.append(f"Turn {t['turn']}: {t['player_action']}")
            if t.get("narrative"):
                lines.append(f"  {t['narrative'][:200]}{'...' if len(t['narrative']) > 200 else ''}")
            for npc_act in t.get("npc_actions", []):
                action = npc_act.get("action", {})
                if action.get("content"):
                    lines.append(f"  {npc_act.get('actor_id')}: {action['content'][:100]}")
        return "\n".join(lines)
