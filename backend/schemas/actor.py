"""
Actor schema - the unified model for players and NPCs.

Every participant in the game (player or NPC) is an Actor.
The only difference is who provides the action: a human for the player,
the LLM for everyone else.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Goal(BaseModel):
    """A goal an actor is pursuing."""

    id: str = Field(..., description="Unique goal identifier")
    description: str = Field(..., description="What the actor wants to achieve")
    priority: Literal["critical", "high", "medium", "low"] = Field(
        default="medium", description="How important this goal is to the actor"
    )
    status: Literal["active", "completed", "failed", "dormant"] = Field(
        default="active", description="Current status of this goal"
    )
    private: bool = Field(
        default=True,
        description="If True, this goal is hidden from the player's view",
    )


class Relationship(BaseModel):
    """How one actor feels about another."""

    actor_id: str = Field(..., description="The other actor's ID")
    score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Sentiment score: -1.0 (hostile) to 1.0 (devoted)",
    )
    summary: str = Field(
        default="",
        description="Short summary of their history, e.g. 'Saved Marcus during the ambush. He owes her.'",
    )
    last_interaction_turn: int = Field(
        default=0, description="Turn number of their last interaction"
    )


class SeedMemory(BaseModel):
    """
    A memory to seed into an actor at session start.

    These represent things the actor already knows before the story begins —
    their history, places they've been, people they know.
    """

    content: str = Field(..., description="The memory content")
    tags: List[str] = Field(
        default=[],
        description="Tags for retrieval: location ids, actor ids, topic keywords",
    )
    visibility: Literal["private", "public"] = Field(
        default="private",
        description="Private = only this actor knows; public = world event everyone knows",
    )


class Actor(BaseModel):
    """
    A participant in the game — player or NPC.

    Actors have their own identity, goals, and history. NPCs act autonomously
    each turn based on their goals and what they know (not what the player knows).
    """

    id: str = Field(..., description="Unique actor identifier")
    name: str = Field(..., description="Display name")
    is_player: bool = Field(
        default=False,
        description="True for the human-controlled character, False for NPCs",
    )
    personality: str = Field(
        ...,
        description="2-3 sentences describing how this actor thinks and behaves",
    )
    background: str = Field(
        ...,
        description="2-3 sentences of backstory — where they came from, what shaped them",
    )
    goals: List[Goal] = Field(
        default=[],
        description="What this actor is trying to achieve. NPCs pursue these autonomously.",
    )
    location_id: str = Field(..., description="Current location ID")
    state: Dict[str, Any] = Field(
        default={},
        description="Mutable actor state: health, mood, inventory, resources, etc.",
    )
    relationships: List[Relationship] = Field(
        default=[],
        description="How this actor feels about other actors",
    )
    known_facts: List[str] = Field(
        default=[],
        description=(
            "Bullet-point summary of important things this actor knows. "
            "Always included in their context. Updated by the summarizer every N turns. "
            "This is how 'events from 35 turns ago' survive — as distilled facts."
        ),
    )
    seed_memories: List[SeedMemory] = Field(
        default=[],
        description=(
            "Memories to load into the memory log at session start. "
            "Not stored on the actor after initialization — they live in memory_entries."
        ),
    )
