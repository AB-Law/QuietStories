"""
Simplified scenario schema definitions.

This module defines the simplified architecture that replaces the complex
ScenarioSpec-based approach with a narrative-driven model focused on
world building and character development.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CharacterMemory(BaseModel):
    """A single character memory entry"""

    content: str = Field(..., description="Memory content")
    importance: int = Field(
        default=5, ge=1, le=10, description="Memory importance (1-10)"
    )
    scope: str = Field(
        default="general", description="Memory scope (general, relationship, knowledge)"
    )
    turn: int = Field(default=0, description="Turn when memory was created")


class CharacterProfile(BaseModel):
    """Character profile with background and memories"""

    id: str = Field(..., description="Unique character identifier")
    name: str = Field(..., description="Character name")
    type: str = Field(default="character", description="Entity type")
    background: str = Field(..., description="Detailed character background narrative")
    personality_traits: List[str] = Field(
        default_factory=list, description="Key personality traits"
    )
    goals: List[str] = Field(default_factory=list, description="Character goals")
    relationships: Dict[str, str] = Field(
        default_factory=dict,
        description="Relationships with other characters (id -> description)",
    )
    memories: List[CharacterMemory] = Field(
        default_factory=list, description="Character memories"
    )
    stats: Optional[Dict[str, Any]] = Field(
        None, description="Optional character stats"
    )


class WorldBackground(BaseModel):
    """World background and setting information"""

    description: str = Field(..., description="Rich world background narrative")
    themes: List[str] = Field(default_factory=list, description="Story themes")
    setting: str = Field(..., description="Time period and location setting")
    key_locations: List[str] = Field(
        default_factory=list, description="Important locations"
    )
    factions: List[str] = Field(default_factory=list, description="Key factions/groups")
    tone: str = Field(
        default="balanced", description="Story tone (dark, light, balanced, etc.)"
    )


class SimplifiedScenario(BaseModel):
    """Simplified scenario specification focusing on narrative elements"""

    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Scenario name")
    description: str = Field(..., description="Original user description")
    world_background: WorldBackground = Field(
        ..., description="World setting and background"
    )
    characters: List[CharacterProfile] = Field(
        default_factory=list, description="Character profiles"
    )
    initial_state: Dict[str, Any] = Field(
        default_factory=dict, description="Optional initial game state"
    )
    difficulty_hints: Optional[Dict[str, str]] = Field(
        None, description="Optional difficulty hints for the narrator"
    )
    suggested_actions: List[str] = Field(
        default_factory=list,
        description="Suggested action types (not rigid rules)",
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    status: str = Field(default="generated", description="Scenario status")


class ScenarioGenerationRequest(BaseModel):
    """Request for simplified scenario generation"""

    description: str = Field(..., description="Free-text scenario description")
    num_characters: int = Field(
        default=3, ge=1, le=10, description="Number of characters to generate"
    )
    include_player: bool = Field(
        default=True, description="Whether to include a player character"
    )
    player_name: Optional[str] = Field(None, description="Player character name")
    difficulty: str = Field(
        default="balanced", description="Difficulty preference (easy, balanced, hard)"
    )


class ScenarioGenerationResponse(BaseModel):
    """Response from simplified scenario generation"""

    id: str = Field(..., description="Scenario ID")
    name: str = Field(..., description="Scenario name")
    status: str = Field(default="generated", description="Generation status")
    character_count: int = Field(..., description="Number of characters generated")
    has_world_background: bool = Field(
        ..., description="Whether world background was generated"
    )
