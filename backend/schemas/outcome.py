"""
Outcome schema definitions for turn results
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class StateChange(BaseModel):
    """State change operation"""

    op: str = Field(..., description="Operation type")
    path: str = Field(..., description="JSON pointer path to modify")
    value: Optional[Any] = Field(None, description="Value for the operation")

    @validator("op")
    def validate_op(cls, v):
        allowed_ops = {"set", "inc", "dec", "mul", "patch", "push", "pop", "addlog"}
        if v not in allowed_ops:
            raise ValueError(f"Invalid operation: {v}. Must be one of {allowed_ops}")
        return v


class VisibleDialogue(BaseModel):
    """Visible dialogue between entities"""

    entity_id: str = Field(..., description="Entity identifier")
    utterance: str = Field(..., description="What the entity says")


class RollRequest(BaseModel):
    """Dice roll request"""

    kind: str = Field(..., description="Type of roll (e.g., 'd20', 'd6', 'custom')")
    target: Optional[str] = Field(None, description="Target entity for the roll")
    difficulty: int = Field(..., description="Difficulty class or target number")


class HiddenMemoryUpdate(BaseModel):
    """Hidden memory update for private thoughts"""

    scope: str = Field(..., description="Memory scope (e.g., 'private', 'entity')")
    target_id: str = Field(..., description="Target entity ID")
    content: str = Field(..., description="Memory content")
    visibility: str = Field(..., description="Visibility level")


class EmotionalStateUpdate(BaseModel):
    """Emotional state update for entities"""

    entity_id: str = Field(
        ..., description="Entity whose emotional state is being updated"
    )
    emotion: str = Field(
        ...,
        description="Primary emotion (joy, sadness, anger, fear, disgust, surprise, trust, anticipation)",
    )
    intensity: float = Field(..., description="Emotional intensity from -1.0 to 1.0")
    cause: Optional[str] = Field(None, description="What caused this emotional state")
    target_entity: Optional[str] = Field(
        None, description="Entity this emotion is directed toward"
    )


class Outcome(BaseModel):
    """Turn outcome from the narrator"""

    narrative: str = Field(..., description="Visible narration text")
    visible_dialogue: Optional[List[VisibleDialogue]] = Field(
        default=None, description="Visible dialogue between entities"
    )
    state_changes: List[StateChange] = Field(
        default_factory=list, description="List of state changes to apply"
    )
    state_changes_summary: Optional[List[str]] = Field(
        default=None, description="Human-readable summary of state changes"
    )
    roll_requests: Optional[List[RollRequest]] = Field(
        default=None, description="Dice roll requests"
    )
    hidden_memory_updates: Optional[List[HiddenMemoryUpdate]] = Field(
        default=None, description="Hidden memory updates"
    )
    emotional_state_updates: Optional[List[EmotionalStateUpdate]] = Field(
        default=None, description="Emotional state updates for entities"
    )
    suggested_actions: Optional[List[str]] = Field(
        default=None, description="Suggested actions for the player to take next"
    )

    class Config:
        extra = "forbid"  # Reject unknown keys (additionalProperties: false)
