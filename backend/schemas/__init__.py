"""
Schemas for QuietStories.
"""

from .actor import Actor, Goal, Relationship, SeedMemory
from .outcome import RollRequest, StateChange, VisibleDialogue
from .scenario import Faction, Location, LossCondition, ScenarioSpec, WinCondition, WorldSpec
from .turn import (
    MemoryEntry,
    NarratorOutput,
    NPCAction,
    NPCDecision,
    OffSceneNPCDecision,
    RollResult,
    TurnInput,
    TurnOutput,
)
from .validation import (
    validate_narrator_output,
    validate_npc_decision,
    validate_off_scene_decision,
    validate_scenario_spec,
)

__all__ = [
    # Actor
    "Actor",
    "Goal",
    "Relationship",
    "SeedMemory",
    # Scenario
    "ScenarioSpec",
    "WorldSpec",
    "Location",
    "Faction",
    "WinCondition",
    "LossCondition",
    # Outcome primitives
    "StateChange",
    "VisibleDialogue",
    "RollRequest",
    # Turn
    "TurnInput",
    "TurnOutput",
    "NarratorOutput",
    "NPCDecision",
    "NPCAction",
    "OffSceneNPCDecision",
    "MemoryEntry",
    "RollResult",
    # Validation
    "validate_scenario_spec",
    "validate_narrator_output",
    "validate_npc_decision",
    "validate_off_scene_decision",
]
