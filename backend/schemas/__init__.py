"""
JSON schemas and validation for the Dynamic CYOA Engine
"""

from .scenario import ScenarioSpec, Action, RandomEvent, EffectOp, LossCondition, NegativityBudget
from .outcome import Outcome, StateChange, RollRequest, HiddenMemoryUpdate, VisibleDialogue
from .validation import validate_scenario_spec, validate_outcome

__all__ = [
    "ScenarioSpec",
    "Action", 
    "RandomEvent",
    "EffectOp",
    "LossCondition",
    "NegativityBudget",
    "Outcome",
    "StateChange",
    "RollRequest", 
    "HiddenMemoryUpdate",
    "VisibleDialogue",
    "validate_scenario_spec",
    "validate_outcome",
]
