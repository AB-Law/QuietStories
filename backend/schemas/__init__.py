"""
JSON schemas and validation for the Dynamic CYOA Engine
"""

from .outcome import (
    HiddenMemoryUpdate,
    Outcome,
    RollRequest,
    StateChange,
    VisibleDialogue,
)
from .scenario import (
    Action,
    EffectOp,
    LossCondition,
    NegativityBudget,
    RandomEvent,
    ScenarioSpec,
)
from .validation import validate_outcome, validate_scenario_spec

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
