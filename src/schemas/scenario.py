"""
ScenarioSpec schema definitions
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class EffectOp(BaseModel):
    """Effect operation for state changes"""
    op: str = Field(..., description="Operation type")
    path: str = Field(..., description="JSON pointer path to modify")
    value: Optional[Any] = Field(None, description="Value for the operation")
    
    @validator('op')
    def validate_op(cls, v):
        allowed_ops = {'set', 'inc', 'dec', 'mul', 'patch', 'push', 'pop', 'addlog'}
        if v not in allowed_ops:
            raise ValueError(f"Invalid operation: {v}. Must be one of {allowed_ops}")
        return v


class Action(BaseModel):
    """Action definition for scenarios"""
    id: str = Field(..., description="Unique action identifier")
    params: Dict[str, Any] = Field(..., description="Parameter schema")
    preconditions: Dict[str, Any] = Field(..., description="JSONLogic preconditions")
    derives: Optional[Dict[str, Any]] = Field(None, description="Derived values")
    effects: List[EffectOp] = Field(..., description="List of effects to apply")


class RandomEvent(BaseModel):
    """Random event definition"""
    id: str = Field(..., description="Unique event identifier")
    weight: float = Field(..., ge=0.05, le=0.30, description="Event weight (0.05-0.30)")
    when: Dict[str, Any] = Field(..., description="JSONLogic condition for when event occurs")
    effects: List[EffectOp] = Field(..., description="List of effects to apply")
    duration: Optional[str] = Field(None, description="Event duration (ISO-like format)")


class LossCondition(BaseModel):
    """Loss condition definition"""
    id: str = Field(..., description="Unique condition identifier")
    condition: Dict[str, Any] = Field(..., description="JSONLogic condition for loss")
    message: str = Field(..., description="Loss message")


class NegativityBudget(BaseModel):
    """Negativity budget configuration"""
    min_fail_rate: float = Field(..., ge=0.0, le=1.0, description="Minimum failure rate")
    decay_per_turn: Dict[str, float] = Field(..., description="Decay rates per turn")


class ScenarioSpec(BaseModel):
    """Complete scenario specification"""
    spec_version: str = Field(default="1.0", description="Specification version")
    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Scenario name")
    seed: int = Field(..., description="Random seed for reproducibility")
    state: Dict[str, Any] = Field(..., description="Initial state object")
    entities: List[Dict[str, Any]] = Field(default=[], description="Entity definitions")
    actions: List[Action] = Field(..., description="Available actions")
    random_events: List[RandomEvent] = Field(..., description="Random events")
    loss_conditions: List[LossCondition] = Field(..., min_items=2, description="Loss conditions (≥2 required)")
    negativity_budget: NegativityBudget = Field(..., description="Negativity budget configuration")
    
    @validator('loss_conditions')
    def validate_loss_conditions(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 loss conditions are required")
        return v
    
    @validator('negativity_budget')
    def validate_negativity_budget(cls, v):
        if v.min_fail_rate <= 0:
            raise ValueError("Negativity budget must have non-zero min_fail_rate")
        return v
