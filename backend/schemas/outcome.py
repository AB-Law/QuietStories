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
    
    @validator('op')
    def validate_op(cls, v):
        allowed_ops = {'set', 'inc', 'dec', 'mul', 'patch', 'push', 'pop', 'addlog'}
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


class Outcome(BaseModel):
    """Turn outcome from the narrator"""
    narrative: str = Field(..., description="Visible narration text")
    visible_dialogue: Optional[List[VisibleDialogue]] = Field(
        None, description="Visible dialogue between entities"
    )
    state_changes: List[StateChange] = Field(
        ..., description="List of state changes to apply"
    )
    roll_requests: Optional[List[RollRequest]] = Field(
        None, description="Dice roll requests"
    )
    hidden_memory_updates: Optional[List[HiddenMemoryUpdate]] = Field(
        None, description="Hidden memory updates"
    )
    
    class Config:
        extra = "forbid"  # Reject unknown keys (additionalProperties: false)
