"""
Turn engine — the main game loop.

Wires together narrator → NPC engine → memory writes → summarizer → turn log.
One public method: process_turn()

Full turn sequence:
  1.  Narrator resolves player action → NarratorOutput
  2.  Write narrator memories to DB
  3.  NPC engine runs all active NPCs → List[NPCDecision | OffSceneNPCDecision]
  4.  Write NPC memories and thoughts to DB
  5.  Update actor last_action_turn
  6.  Check win/loss conditions
  7.  Run memory summarizer (if on interval)
  8.  Advance turn counter
  9.  Log the full turn
  10. Assemble and return TurnOutput
"""

import random
from typing import Any, Dict, List, Union

from backend.db.manager import DatabaseManager
from backend.engine.memory import MemoryManager
from backend.engine.narrator import Narrator
from backend.engine.npc_engine import NPCEngine
from backend.providers.base import BaseProvider
from backend.schemas.scenario import ScenarioSpec
from backend.schemas.turn import (
    MemoryEntry,
    NPCDecision,
    OffSceneNPCDecision,
    RollResult,
    TurnInput,
    TurnOutput,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TurnEngine:
    """Processes one player turn end-to-end."""

    def __init__(
        self,
        db: DatabaseManager,
        provider: BaseProvider,
        spec: ScenarioSpec,
    ):
        self.db = db
        self.provider = provider
        self.spec = spec
        self.narrator = Narrator(db, provider)
        self.npc_engine = NPCEngine(db, provider)
        self.memory = MemoryManager(db, provider)

    async def process_turn(self, turn_input: TurnInput) -> TurnOutput:
        """
        Process one player turn and return what the player sees.
        """
        session_id = turn_input.session_id
        player_action = turn_input.action.strip()

        session = self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session["status"] != "active":
            raise ValueError(f"Session {session_id} is not active (status: {session['status']})")

        current_turn = session["turn"] + 1
        logger.info(f"[Turn {current_turn}] Player: {player_action[:60]}...")

        # ── 1. Narrator resolves player action ──────────────────────────
        narrator_output = await self.narrator.resolve_turn(session_id, player_action)

        # ── 2. Write narrator memories ───────────────────────────────────
        if narrator_output.new_memories:
            self.memory.write_memories(session_id, current_turn, narrator_output.new_memories)

        # ── 3. NPC turns ─────────────────────────────────────────────────
        npc_decisions = await self.npc_engine.run_npc_turns(session_id, current_turn)

        # ── 4. Write NPC memories and private thoughts ───────────────────
        for decision in npc_decisions:
            if decision.new_memories:
                self.memory.write_memories(session_id, current_turn, decision.new_memories)
            # Store private thought as memory (never sent to player)
            thought = getattr(decision, "private_thought", None) or getattr(decision, "summary", None)
            if thought:
                player = self.db.get_player_actor(session_id)
                scene_tags = [player["location_id"]] if player else []
                self.memory.write_npc_thought(
                    session_id, decision.actor_id, current_turn, thought, tags=scene_tags
                )

        # ── 5. Update actor last_action_turn ─────────────────────────────
        player = self.db.get_player_actor(session_id)
        if player:
            self.db.save_actor(session_id, player["actor_id"], {"last_action_turn": current_turn})
        for decision in npc_decisions:
            self.db.save_actor(
                session_id, decision.actor_id, {"last_action_turn": current_turn}
            )

        # ── 6. Resolve dice rolls ─────────────────────────────────────────
        roll_results = _resolve_rolls(narrator_output.roll_requests)

        # ── 7. Run memory summarizer ──────────────────────────────────────
        await self.memory.maybe_summarize(session_id, current_turn)

        # ── 9. Advance turn counter ───────────────────────────────────────
        self.db.update_session(session_id, turn=current_turn)

        # ── 10. Log the full turn ─────────────────────────────────────────
        self.db.append_turn(
            session_id=session_id,
            turn=current_turn,
            player_action=player_action,
            narrator_output=narrator_output.model_dump(),
            npc_decisions=[d.model_dump() for d in npc_decisions],
            roll_results=[r.model_dump() for r in roll_results],
        )

        logger.info(f"[Turn {current_turn}] Complete — {len(npc_decisions)} NPC decisions")

        # ── 11. Assemble TurnOutput (strip private NPC data) ──────────────
        visible_npc_decisions = _filter_visible_npc_decisions(npc_decisions)

        # Merge in-scene NPC dialogue into visible_dialogue
        visible_dialogue = list(narrator_output.visible_dialogue)
        for decision in visible_npc_decisions:
            action = decision.action
            if action and action.type == "speak" and action.content and action.visible_to_player:
                from backend.schemas.outcome import VisibleDialogue
                visible_dialogue.append(
                    VisibleDialogue(entity_id=decision.actor_id, utterance=action.content)
                )

        return TurnOutput(
            turn=current_turn,
            narrative=narrator_output.narrative,
            visible_dialogue=visible_dialogue,
            npc_actions=visible_npc_decisions,
            roll_results=roll_results,
            suggested_actions=narrator_output.suggested_actions,
            game_over=False,
            win=False,
        )


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _resolve_rolls(
    roll_requests: List[Any],
) -> List[RollResult]:
    """Simulate dice rolls for all requested checks."""
    results = []
    for req in roll_requests:
        roll = random.randint(1, 20)
        results.append(
            RollResult(
                kind=req.kind,
                difficulty=req.difficulty,
                roll=roll,
                success=roll >= req.difficulty,
                target_id=req.target_id,
            )
        )
    return results


def _filter_visible_npc_decisions(
    decisions: List[Union[NPCDecision, OffSceneNPCDecision]],
) -> List[NPCDecision]:
    """
    Strip private NPC data before sending to the frontend.

    - Removes private_thought entirely
    - Removes actions with visible_to_player=False
    - Converts OffSceneNPCDecision to NPCDecision with stripped fields
    """
    visible = []
    for d in decisions:
        action = getattr(d, "action", None)

        # For OffSceneNPCDecision, grab first visible action if any
        if isinstance(d, OffSceneNPCDecision):
            action = next(
                (a for a in (d.actions or []) if a.visible_to_player), None
            )

        if action and not action.visible_to_player:
            action = None

        if action is None and not isinstance(d, OffSceneNPCDecision):
            # In-scene NPC with no visible action — skip
            continue

        visible.append(
            NPCDecision(
                actor_id=d.actor_id,
                private_thought="",  # stripped
                action=action,
                new_memories=[],     # stripped
                state_changes=[],    # stripped
            )
        )
    return visible
