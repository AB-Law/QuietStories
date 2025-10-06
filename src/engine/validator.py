"""
Scenario validator with Monte Carlo simulation for auto-balancing
"""

import random
import json
from typing import Dict, Any, List, Tuple
from ..schemas import ScenarioSpec, validate_scenario_spec
from ..config import settings


class ScenarioValidator:
    """Validates scenario specifications and performs auto-balancing"""
    
    def __init__(self):
        self.monte_carlo_turns = settings.monte_carlo_turns
        self.min_fail_rate = settings.negativity_min_fail_rate
    
    def validate_spec(self, spec_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a scenario specification"""
        issues = []
        
        try:
            # Parse and validate the spec
            spec = validate_scenario_spec(spec_data)
            
            # Check negativity budget
            if spec.negativity_budget.min_fail_rate <= 0:
                issues.append("Negativity budget must have non-zero min_fail_rate")
            
            # Check loss conditions
            if len(spec.loss_conditions) < 2:
                issues.append("At least 2 loss conditions are required")
            
            # Check random event weights
            for event in spec.random_events:
                if not (0.05 <= event.weight <= 0.30):
                    issues.append(f"Event {event.id} weight {event.weight} must be between 0.05-0.30")
            
            # Check for forbidden scenario nouns (empty list by default)
            forbidden_nouns = []  # Can be configured later
            for key, value in spec_data.items():
                if isinstance(value, str):
                    if any(noun.lower() in value.lower() for noun in forbidden_nouns):
                        issues.append(f"Forbidden scenario noun found in {key}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Schema validation failed: {e}")
            return False, issues
    
    def monte_carlo_simulation(self, spec: ScenarioSpec) -> Tuple[bool, Dict[str, Any]]:
        """Run Monte Carlo simulation to test scenario difficulty"""
        
        results = {
            "total_simulations": self.monte_carlo_turns,
            "failures": 0,
            "successes": 0,
            "avg_turns_to_failure": 0,
            "avg_turns_to_success": 0,
            "fail_rate": 0.0,
            "passed": False
        }
        
        failure_turns = []
        success_turns = []
        
        for simulation in range(self.monte_carlo_turns):
            # Create a deep copy of the spec for this simulation
            sim_spec = spec.copy(deep=True)
            sim_spec.seed = random.randint(1, 1000000)
            
            # Simulate the scenario
            outcome = self._simulate_scenario(sim_spec)
            
            if outcome["result"] == "failure":
                results["failures"] += 1
                failure_turns.append(outcome["turns"])
            elif outcome["result"] == "success":
                results["successes"] += 1
                success_turns.append(outcome["turns"])
        
        # Calculate statistics
        results["fail_rate"] = results["failures"] / self.monte_carlo_turns
        
        if failure_turns:
            results["avg_turns_to_failure"] = sum(failure_turns) / len(failure_turns)
        
        if success_turns:
            results["avg_turns_to_success"] = sum(success_turns) / len(success_turns)
        
        # Check if scenario meets difficulty requirements
        results["passed"] = results["fail_rate"] >= self.min_fail_rate
        
        return results["passed"], results
    
    def _simulate_scenario(self, spec: ScenarioSpec) -> Dict[str, Any]:
        """Simulate a single scenario run"""
        
        # Initialize state
        state = spec.state.copy()
        turn = 0
        max_turns = 50  # Prevent infinite loops
        
        while turn < max_turns:
            turn += 1
            
            # Check loss conditions
            for loss_condition in spec.loss_conditions:
                if self._evaluate_condition(loss_condition.condition, state):
                    return {"result": "failure", "turns": turn, "reason": loss_condition.id}
            
            # Simulate random events
            for event in spec.random_events:
                if self._evaluate_condition(event.when, state):
                    # Roll for event occurrence
                    if random.random() < event.weight:
                        # Apply event effects
                        state = self._apply_effects(state, event.effects)
            
            # Simulate action selection (baseline policy)
            available_actions = self._get_available_actions(spec.actions, state)
            if not available_actions:
                return {"result": "failure", "turns": turn, "reason": "no_actions"}
            
            # Select random action
            action = random.choice(available_actions)
            state = self._apply_effects(state, action.effects)
            
            # Check for success conditions (if any)
            # This would need to be defined in the spec
        
        return {"result": "timeout", "turns": turn, "reason": "max_turns_reached"}
    
    def _evaluate_condition(self, condition: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """Evaluate a JSONLogic condition against the current state"""
        try:
            from ..utils.jsonlogic import JSONLogicEvaluator
            evaluator = JSONLogicEvaluator()
            return evaluator.evaluate_condition(condition, state)
        except Exception:
            return False
    
    def _get_available_actions(self, actions: List, state: Dict[str, Any]) -> List:
        """Get actions that are available given current state"""
        available = []
        for action in actions:
            if self._evaluate_condition(action.preconditions, state):
                available.append(action)
        return available
    
    def _apply_effects(self, state: Dict[str, Any], effects: List) -> Dict[str, Any]:
        """Apply effects to the state"""
        new_state = state.copy()
        
        for effect in effects:
            # This is a simplified implementation
            # In practice, you'd implement proper JSON pointer path resolution
            if effect.op == "set":
                # Set a value at the path
                pass
            elif effect.op == "inc":
                # Increment a value at the path
                pass
            # ... other operations
        
        return new_state
    
    def auto_repair(self, spec_data: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Attempt to auto-repair a scenario specification"""
        
        repaired = spec_data.copy()
        
        # Fix negativity budget
        if "Negativity budget must have non-zero min_fail_rate" in issues:
            if "negativity_budget" not in repaired:
                repaired["negativity_budget"] = {}
            repaired["negativity_budget"]["min_fail_rate"] = 0.25
            repaired["negativity_budget"]["decay_per_turn"] = {}
        
        # Fix loss conditions
        if "At least 2 loss conditions are required" in issues:
            if "loss_conditions" not in repaired or len(repaired["loss_conditions"]) < 2:
                repaired["loss_conditions"] = [
                    {
                        "id": "health_loss",
                        "condition": {"<": [{"var": "state.health"}, 0]},
                        "message": "You have died."
                    },
                    {
                        "id": "time_loss", 
                        "condition": {">": [{"var": "state.turns"}, 100]},
                        "message": "Time has run out."
                    }
                ]
        
        # Fix random event weights
        if "random_events" in repaired:
            for event in repaired["random_events"]:
                if "weight" in event:
                    if event["weight"] < 0.05:
                        event["weight"] = 0.05
                    elif event["weight"] > 0.30:
                        event["weight"] = 0.30
        
        return repaired
