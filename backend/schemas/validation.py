"""
Schema validation utilities.
"""

from typing import Any, Dict

from .actor import Actor
from .scenario import ScenarioSpec
from .turn import NarratorOutput, NPCDecision, OffSceneNPCDecision


def validate_scenario_spec(spec_data: Dict[str, Any]) -> ScenarioSpec:
    """Validate and parse a scenario specification."""
    try:
        return ScenarioSpec(**spec_data)
    except Exception as e:
        raise ValueError(f"Invalid scenario spec: {e}")


def validate_narrator_output(data: Dict[str, Any]) -> NarratorOutput:
    """Validate and parse narrator LLM output."""
    try:
        return NarratorOutput(**data)
    except Exception as e:
        raise ValueError(f"Invalid narrator output: {e}")


def validate_npc_decision(data: Dict[str, Any]) -> NPCDecision:
    """Validate and parse an NPC decision LLM output."""
    try:
        return NPCDecision(**data)
    except Exception as e:
        raise ValueError(f"Invalid NPC decision: {e}")


def validate_off_scene_decision(data: Dict[str, Any]) -> OffSceneNPCDecision:
    """Validate and parse an off-scene NPC decision."""
    try:
        return OffSceneNPCDecision(**data)
    except Exception as e:
        raise ValueError(f"Invalid off-scene NPC decision: {e}")
