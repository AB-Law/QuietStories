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
from .simplified import (
    CharacterMemory,
    CharacterProfile,
    ScenarioGenerationRequest,
    ScenarioGenerationResponse,
    SimplifiedScenario,
    WorldBackground,
)
from .validation import validate_outcome, validate_scenario_spec

__all__ = [
    # Legacy ScenarioSpec models (kept for backward compatibility)
    "ScenarioSpec",
    "Action",
    "RandomEvent",
    "EffectOp",
    "LossCondition",
    "NegativityBudget",
    # Simplified models
    "SimplifiedScenario",
    "WorldBackground",
    "CharacterProfile",
    "CharacterMemory",
    "ScenarioGenerationRequest",
    "ScenarioGenerationResponse",
    # Outcome models (unchanged)
    "Outcome",
    "StateChange",
    "RollRequest",
    "HiddenMemoryUpdate",
    "VisibleDialogue",
    # Validation functions
    "validate_scenario_spec",
    "validate_outcome",
]
