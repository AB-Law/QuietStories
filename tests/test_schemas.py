"""
Test schema validation
"""

import pytest
from src.schemas import ScenarioSpec, Outcome, validate_scenario_spec, validate_outcome


def test_scenario_spec_validation():
    """Test scenario specification validation"""
    
    valid_spec = {
        "spec_version": "1.0",
        "id": "test_scenario",
        "name": "Test Scenario",
        "seed": 12345,
        "state": {"health": 100, "turns": 0},
        "entities": [],
        "actions": [
            {
                "id": "move",
                "params": {"direction": "string"},
                "preconditions": {"==": [{"var": "state.health"}, 100]},
                "effects": [{"op": "set", "path": "state.turns", "value": 1}]
            }
        ],
        "random_events": [
            {
                "id": "injury",
                "weight": 0.1,
                "when": {"==": [{"var": "state.health"}, 50]},
                "effects": [{"op": "dec", "path": "state.health", "value": 10}]
            }
        ],
        "loss_conditions": [
            {
                "id": "death",
                "condition": {"<": [{"var": "state.health"}, 0]},
                "message": "You have died."
            },
            {
                "id": "timeout",
                "condition": {">": [{"var": "state.turns"}, 100]},
                "message": "Time has run out."
            }
        ],
        "negativity_budget": {
            "min_fail_rate": 0.25,
            "decay_per_turn": {}
        }
    }
    
    # Should validate successfully
    spec = validate_scenario_spec(valid_spec)
    assert spec.id == "test_scenario"
    assert spec.spec_version == "1.0"
    assert len(spec.loss_conditions) >= 2
    assert spec.negativity_budget.min_fail_rate > 0


def test_scenario_spec_validation_failures():
    """Test scenario specification validation failures"""
    
    # Missing required fields
    invalid_spec = {
        "id": "test",
        "name": "Test"
    }
    
    with pytest.raises(ValueError):
        validate_scenario_spec(invalid_spec)
    
    # Insufficient loss conditions
    invalid_spec = {
        "spec_version": "1.0",
        "id": "test",
        "name": "Test",
        "seed": 123,
        "state": {},
        "entities": [],
        "actions": [],
        "random_events": [],
        "loss_conditions": [{"id": "single", "condition": {}, "message": "Only one"}],
        "negativity_budget": {"min_fail_rate": 0.25, "decay_per_turn": {}}
    }
    
    with pytest.raises(ValueError):
        validate_scenario_spec(invalid_spec)


def test_outcome_validation():
    """Test outcome validation"""
    
    valid_outcome = {
        "narrative": "The story continues...",
        "state_changes": [
            {"op": "set", "path": "state.turns", "value": 1}
        ]
    }
    
    outcome = validate_outcome(valid_outcome)
    assert outcome.narrative == "The story continues..."
    assert len(outcome.state_changes) == 1
    assert outcome.state_changes[0].op == "set"


def test_outcome_validation_failures():
    """Test outcome validation failures"""
    
    # Missing required fields
    invalid_outcome = {
        "narrative": "Test"
    }
    
    with pytest.raises(ValueError):
        validate_outcome(invalid_outcome)
    
    # Invalid operation
    invalid_outcome = {
        "narrative": "Test",
        "state_changes": [
            {"op": "invalid", "path": "state.test", "value": 1}
        ]
    }
    
    with pytest.raises(ValueError):
        validate_outcome(invalid_outcome)
