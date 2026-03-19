"""
Turn schema - inputs and outputs for each game turn.

A turn consists of:
  1. Player submits a TurnInput
  2. Narrator LLM produces a NarratorOutput
  3. Each active NPC produces an NPCDecision
  4. Engine assembles everything into a TurnOutput returned to the frontend
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .outcome import RollRequest, StateChange, VisibleDialogue


class MemoryEntry(BaseModel):
    """
    A memory to write into an actor's memory log.

    Created by the narrator and NPC decision LLMs each turn.
    Stored in the memory_entries table and retrieved selectively in future turns.
    """

    actor_id: str = Field(..., description="Who this memory belongs to")
    content: str = Field(..., description="The memory text")
    tags: List[str] = Field(
        default=[],
        description=(
            "Retrieval tags: include relevant location IDs, actor IDs present, "
            "and topic keywords. E.g. ['loc_market', 'elena', 'betrayal']"
        ),
    )
    visibility: str = Field(
        default="private",
        description="'private' = only this actor knows; 'public' = all actors learn it",
    )


class NPCActionType:
    SPEAK = "speak"
    MOVE = "move"
    INTERACT = "interact"
    PURSUE_GOAL = "pursue_goal"
    OBSERVE = "observe"


class NPCAction(BaseModel):
    """A concrete action taken by an NPC during their turn."""

    type: str = Field(
        ...,
        description="Action type: speak, move, interact, pursue_goal, observe",
    )
    target_id: Optional[str] = Field(
        None,
        description="Actor ID or location ID this action is directed at",
    )
    content: Optional[str] = Field(
        None,
        description="Dialogue text for 'speak', description for other types",
    )
    visible_to_player: bool = Field(
        default=True,
        description="Whether the player can observe this action",
    )


class NPCDecision(BaseModel):
    """
    What an NPC decides to think and do during their turn.

    This is the raw output of the NPC decision LLM.
    private_thought is stored as a memory but never shown to the player.
    """

    actor_id: str = Field(..., description="Which NPC made this decision")
    private_thought: str = Field(
        ...,
        description=(
            "What the NPC is thinking — their internal reasoning. "
            "Stored as a private memory, never shown to the player."
        ),
    )
    action: Optional[NPCAction] = Field(
        None,
        description="What the NPC does. None if they stay still / observe.",
    )
    new_memories: List[MemoryEntry] = Field(
        default=[],
        description="Memories to record based on what happened this turn",
    )
    state_changes: List[StateChange] = Field(
        default=[],
        description="Any state mutations caused by this NPC's action",
    )


class NarratorOutput(BaseModel):
    """
    Structured output from the narrator LLM after resolving the player's action.

    The narrator describes what happens and records memories.
    It does NOT manage NPC decisions — those are handled by the NPC engine.
    """

    narrative: str = Field(
        ...,
        description=(
            "The story text shown to the player. "
            "Pure storytelling only — no stat numbers, no +X/-X, no meta-game info."
        ),
    )
    visible_dialogue: List[VisibleDialogue] = Field(
        default=[],
        description="Dialogue spoken aloud by characters in the scene",
    )
    state_changes: List[StateChange] = Field(
        default=[],
        description="State mutations to apply after this turn",
    )
    new_memories: List[MemoryEntry] = Field(
        default=[],
        description=(
            "Memories to record for actors based on what happened. "
            "Include memories for the player AND any NPCs who witnessed events."
        ),
    )
    roll_requests: List[RollRequest] = Field(
        default=[],
        description="Dice rolls needed to resolve uncertain outcomes",
    )
    suggested_actions: List[str] = Field(
        default=[],
        description="3-5 contextual action suggestions for the player",
    )


class RollResult(BaseModel):
    """Result of a resolved dice roll."""

    kind: str
    difficulty: int
    roll: int
    success: bool
    target_id: Optional[str] = None


class TurnInput(BaseModel):
    """What the player submits to take a turn."""

    session_id: str = Field(..., description="Active session ID")
    action: str = Field(..., description="Free-text description of what the player does")


class TurnOutput(BaseModel):
    """
    The complete result of a turn, returned to the frontend.

    Assembles the narrator output + NPC decisions into what the player sees.
    NPC actions that are not visible_to_player are filtered out before sending.
    """

    turn: int = Field(..., description="Turn number after this action")
    narrative: str = Field(..., description="Main story text from the narrator")
    visible_dialogue: List[VisibleDialogue] = Field(
        default=[],
        description="Dialogue spoken aloud this turn (player + NPCs)",
    )
    npc_actions: List[NPCDecision] = Field(
        default=[],
        description="NPC decisions visible to the player (private_thought is stripped)",
    )
    roll_results: List[RollResult] = Field(
        default=[],
        description="Outcomes of any dice rolls this turn",
    )
    suggested_actions: List[str] = Field(
        default=[],
        description="Suggested next actions for the player",
    )
    game_over: bool = Field(default=False)
    game_over_message: Optional[str] = Field(default=None)
    win: bool = Field(default=False)


class OffSceneNPCDecision(BaseModel):
    """
    What an off-scene NPC did during the turns they were inactive.

    Off-scene NPCs act every N turns and summarize what they did over that period.
    """

    actor_id: str = Field(..., description="Which NPC made this decision")
    turns_elapsed: int = Field(..., description="How many turns passed since last action")
    summary: str = Field(
        ...,
        description="What the NPC did during this period, from their perspective",
    )
    actions: List[NPCAction] = Field(
        default=[],
        description="The specific actions taken during this period",
    )
    new_memories: List[MemoryEntry] = Field(
        default=[],
        description="Memories accumulated during this off-scene period",
    )
    state_changes: List[StateChange] = Field(
        default=[],
        description="State mutations from off-scene activity",
    )
