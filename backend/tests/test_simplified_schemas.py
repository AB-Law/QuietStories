"""
Tests for simplified scenario generation and orchestration.
"""

import pytest

from backend.schemas.simplified import (
    CharacterMemory,
    CharacterProfile,
    ScenarioGenerationRequest,
    SimplifiedScenario,
    WorldBackground,
)


def test_world_background_model():
    """Test WorldBackground model creation."""
    world = WorldBackground(
        description="A mysterious Victorian London shrouded in fog.",
        themes=["mystery", "gothic", "detective"],
        setting="Victorian London, 1890s",
        key_locations=["Baker Street", "Scotland Yard", "The Thames"],
        factions=["Police", "Criminal Underworld"],
        tone="dark and mysterious",
    )

    assert world.description
    assert len(world.themes) == 3
    assert world.setting == "Victorian London, 1890s"
    assert "Baker Street" in world.key_locations


def test_character_profile_model():
    """Test CharacterProfile model creation."""
    character = CharacterProfile(
        id="sherlock_holmes",
        name="Sherlock Holmes",
        type="character",
        background="The world's greatest consulting detective.",
        personality_traits=["analytical", "eccentric", "brilliant"],
        goals=["Solve the mystery", "Protect London"],
        relationships={"watson": "Trusted friend and colleague"},
        memories=[
            CharacterMemory(
                content="Met Dr. Watson at St. Bartholomew's Hospital",
                importance=8,
                scope="relationship",
                turn=0,
            )
        ],
        stats=None,
    )

    assert character.id == "sherlock_holmes"
    assert character.name == "Sherlock Holmes"
    assert len(character.personality_traits) == 3
    assert len(character.memories) == 1
    assert character.memories[0].content.startswith("Met Dr. Watson")


def test_simplified_scenario_model():
    """Test SimplifiedScenario model creation."""
    world = WorldBackground(
        description="A fantasy realm",
        themes=["fantasy", "adventure"],
        setting="Medieval fantasy world",
        key_locations=["Castle", "Forest"],
        factions=["Kingdom", "Rebels"],
        tone="balanced",
    )

    character = CharacterProfile(
        id="hero",
        name="Hero",
        background="A brave adventurer",
        personality_traits=["brave"],
        goals=["Save the kingdom"],
        stats=None,
    )

    scenario = SimplifiedScenario(
        id="test_scenario",
        name="Test Adventure",
        description="A test scenario",
        world_background=world,
        characters=[character],
        initial_state={"location": "start"},
        suggested_actions=["explore", "fight", "talk"],
        status="generated",
    )

    assert scenario.id == "test_scenario"
    assert scenario.name == "Test Adventure"
    assert len(scenario.characters) == 1
    assert scenario.characters[0].name == "Hero"
    assert "explore" in scenario.suggested_actions


def test_scenario_generation_request_model():
    """Test ScenarioGenerationRequest model validation."""
    request = ScenarioGenerationRequest(
        description="A cyberpunk adventure in Neo Tokyo",
        num_characters=5,
        include_player=True,
        player_name="Alex",
        difficulty="hard",
    )

    assert request.description
    assert request.num_characters == 5
    assert request.include_player is True
    assert request.player_name == "Alex"
    assert request.difficulty == "hard"


def test_scenario_generation_request_defaults():
    """Test ScenarioGenerationRequest default values."""
    request = ScenarioGenerationRequest(
        description="A simple story",
    )

    assert request.num_characters == 3  # default
    assert request.include_player is True  # default
    assert request.player_name is None  # default
    assert request.difficulty == "balanced"  # default


def test_character_memory_importance_validation():
    """Test CharacterMemory importance validation."""
    # Valid importance values
    memory1 = CharacterMemory(content="Test memory", importance=1)
    assert memory1.importance == 1

    memory2 = CharacterMemory(content="Test memory", importance=10)
    assert memory2.importance == 10

    memory3 = CharacterMemory(content="Test memory")  # default
    assert memory3.importance == 5

    # Invalid importance values should be caught by pydantic
    with pytest.raises(Exception):  # ValidationError
        CharacterMemory(content="Test memory", importance=0)

    with pytest.raises(Exception):  # ValidationError
        CharacterMemory(content="Test memory", importance=11)


def test_simplified_scenario_minimal():
    """Test SimplifiedScenario with minimal required fields."""
    world = WorldBackground(
        description="A world",
        setting="Unknown",
        themes=[],
        key_locations=[],
        factions=[],
    )

    scenario = SimplifiedScenario(
        id="minimal",
        name="Minimal Scenario",
        description="Basic test",
        world_background=world,
    )

    assert scenario.id == "minimal"
    assert len(scenario.characters) == 0  # default empty list
    assert len(scenario.initial_state) == 0  # default empty dict
    assert len(scenario.suggested_actions) == 0  # default empty list
