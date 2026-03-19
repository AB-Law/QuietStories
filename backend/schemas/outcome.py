"""
Shared outcome primitives used by both the narrator and NPC decision schemas.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

ALLOWED_OPS = {"set", "inc", "dec", "mul", "patch", "push", "pop", "addlog"}


class StateChange(BaseModel):
    """A single state mutation operation."""

    op: str = Field(..., description=f"Operation type: {', '.join(sorted(ALLOWED_OPS))}")
    path: str = Field(
        ...,
        description="Dot-separated path to the value being modified, e.g. 'global_state.day'",
    )
    value: Optional[Any] = Field(None, description="Value to apply")

    @field_validator("op")
    @classmethod
    def validate_op(cls, v: str) -> str:
        if v not in ALLOWED_OPS:
            raise ValueError(f"Invalid op '{v}'. Must be one of: {sorted(ALLOWED_OPS)}")
        return v


class VisibleDialogue(BaseModel):
    """A line of dialogue spoken aloud in the scene."""

    entity_id: str = Field(..., description="ID of the actor speaking")
    utterance: str = Field(..., description="What they say")


class RollRequest(BaseModel):
    """A dice roll needed to resolve an uncertain outcome."""

    kind: str = Field(
        ...,
        description="Skill or check type, e.g. 'persuasion', 'combat', 'stealth'",
    )
    difficulty: int = Field(
        ...,
        ge=5,
        le=20,
        description="Difficulty class: 5=trivial, 10=moderate, 15=hard, 20=very hard",
    )
    target_id: Optional[str] = Field(
        None, description="Actor ID being targeted, if any"
    )
