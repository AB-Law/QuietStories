"""
ScenarioSpec schema - defines a complete playable scenario.

A scenario has three parts:
  - world: the setting, locations, factions, and rules
  - actors: everyone in the story (player + NPCs), each with full identity
  - conditions: how the game can be won or lost
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .actor import Actor


class Location(BaseModel):
    """A place in the world."""

    id: str = Field(..., description="Unique location identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(
        ..., description="What this place looks, sounds, and feels like"
    )
    connected_to: List[str] = Field(
        default=[],
        description="IDs of locations reachable from here",
    )
    state: Dict[str, Any] = Field(
        default={},
        description="Mutable location state: controlled_by, danger_level, etc.",
    )


class Faction(BaseModel):
    """A group with shared interests."""

    id: str = Field(..., description="Unique faction identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="What this faction wants and how they operate")
    disposition: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Starting disposition toward the player: -1.0 hostile, 1.0 allied",
    )


class WorldSpec(BaseModel):
    """The setting for the story."""

    description: str = Field(
        ...,
        description="Overall world description in 2-3 sentences — the feel and context",
    )
    tone: str = Field(
        ...,
        description="Genre and tone, e.g. 'dark fantasy', 'political thriller', 'space opera'",
    )
    locations: List[Location] = Field(
        ..., description="All named places in the world", min_length=1
    )
    factions: List[Faction] = Field(
        default=[],
        description="Groups the player and NPCs belong to or interact with",
    )
    rules: str = Field(
        default="",
        description="What is and isn't possible in this world — magic system, technology level, etc.",
    )
    initial_time: str = Field(
        default="dawn",
        description="Starting time of day",
    )
    initial_day: int = Field(
        default=1,
        description="Starting day number",
    )


class WinCondition(BaseModel):
    """A way the player can win."""

    id: str = Field(..., description="Unique condition identifier")
    condition: Dict[str, Any] = Field(
        ..., description="JSONLogic expression evaluated against global_state"
    )
    message: str = Field(..., description="Victory message shown to the player")


class LossCondition(BaseModel):
    """A way the player can lose."""

    id: str = Field(..., description="Unique condition identifier")
    condition: Dict[str, Any] = Field(
        ..., description="JSONLogic expression evaluated against global_state"
    )
    message: str = Field(..., description="Defeat message shown to the player")


class ScenarioSpec(BaseModel):
    """
    Complete scenario specification — the blueprint for a game session.

    When a session starts, this spec is used to initialize:
      - world_state (from world)
      - actor records (from actors)
      - memory_entries (from each actor's seed_memories)
    """

    spec_version: str = Field(default="2.0", description="Schema version")
    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Display name")
    seed: int = Field(..., description="Random seed for reproducibility")
    world: WorldSpec = Field(..., description="The world setting")
    actors: List[Actor] = Field(
        ...,
        description="All actors: exactly one must have is_player=True",
        min_length=2,
    )
    win_conditions: List[WinCondition] = Field(
        default=[],
        description="Optional win conditions",
    )
    loss_conditions: List[LossCondition] = Field(
        ...,
        description="How the player can lose — at least one required",
        min_length=1,
    )
    global_state: Dict[str, Any] = Field(
        default={},
        description="Shared mutable state not tied to any actor: day, weather, etc.",
    )

    @field_validator("actors")
    @classmethod
    def must_have_exactly_one_player(cls, actors: List[Actor]) -> List[Actor]:
        player_count = sum(1 for a in actors if a.is_player)
        if player_count != 1:
            raise ValueError(
                f"Scenario must have exactly one actor with is_player=True, found {player_count}"
            )
        return actors

    @field_validator("actors")
    @classmethod
    def actor_ids_must_be_unique(cls, actors: List[Actor]) -> List[Actor]:
        ids = [a.id for a in actors]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate actor IDs: {list(set(duplicates))}")
        return actors

    @field_validator("world")
    @classmethod
    def location_ids_must_be_unique(cls, world: WorldSpec) -> WorldSpec:
        ids = [loc.id for loc in world.locations]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate location IDs: {list(set(duplicates))}")
        return world
