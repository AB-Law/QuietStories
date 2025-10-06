"""
Monte Carlo simulation utilities
"""

import random
from typing import Dict, Any, List, Tuple
from ..schemas import ScenarioSpec


class MonteCarloSimulator:
    """Monte Carlo simulation for scenario testing"""
    
    def __init__(self, num_simulations: int = 100):
        self.num_simulations = num_simulations
    
    def simulate_scenario(self, spec: ScenarioSpec) -> Dict[str, Any]:
        """Run Monte Carlo simulation on a scenario"""
        
        results = {
            "total_simulations": self.num_simulations,
            "failures": 0,
            "successes": 0,
            "timeouts": 0,
            "fail_rate": 0.0,
            "avg_turns_to_failure": 0.0,
            "avg_turns_to_success": 0.0,
            "passed": False
        }
        
        failure_turns = []
        success_turns = []
        
        for i in range(self.num_simulations):
            # Set random seed for this simulation
            random.seed(spec.seed + i)
            
            # Run simulation
            outcome = self._simulate_single_run(spec)
            
            if outcome["result"] == "failure":
                results["failures"] += 1
                failure_turns.append(outcome["turns"])
            elif outcome["result"] == "success":
                results["successes"] += 1
                success_turns.append(outcome["turns"])
            else:
                results["timeouts"] += 1
        
        # Calculate statistics
        results["fail_rate"] = results["failures"] / self.num_simulations
        
        if failure_turns:
            results["avg_turns_to_failure"] = sum(failure_turns) / len(failure_turns)
        
        if success_turns:
            results["avg_turns_to_success"] = sum(success_turns) / len(success_turns)
        
        # Check if scenario meets difficulty requirements
        min_fail_rate = spec.negativity_budget.min_fail_rate
        results["passed"] = results["fail_rate"] >= min_fail_rate
        
        return results
    
    def _simulate_single_run(self, spec: ScenarioSpec) -> Dict[str, Any]:
        """Simulate a single scenario run"""
        
        # Initialize state
        state = spec.state.copy()
        turn = 0
        max_turns = 100  # Prevent infinite loops
        
        while turn < max_turns:
            turn += 1
            
            # Check loss conditions
            for loss_condition in spec.loss_conditions:
                if self._evaluate_loss_condition(loss_condition, state):
                    return {
                        "result": "failure",
                        "turns": turn,
                        "reason": loss_condition.id
                    }
            
            # Simulate random events
            for event in spec.random_events:
                if self._should_trigger_event(event, state):
                    self._apply_event_effects(event, state)
            
            # Simulate action selection (baseline policy)
            available_actions = self._get_available_actions(spec.actions, state)
            if not available_actions:
                return {
                    "result": "failure",
                    "turns": turn,
                    "reason": "no_actions"
                }
            
            # Select random action
            action = random.choice(available_actions)
            self._apply_action_effects(action, state)
            
            # Check for success conditions (if any)
            # This would need to be defined in the spec
        
        return {
            "result": "timeout",
            "turns": turn,
            "reason": "max_turns_reached"
        }
    
    def _evaluate_loss_condition(self, loss_condition, state: Dict[str, Any]) -> bool:
        """Evaluate a loss condition against the current state"""
        
        # Simplified evaluation - in production, use proper JSONLogic evaluator
        try:
            # Check if the condition is met
            condition = loss_condition.condition
            if isinstance(condition, dict):
                # Simple condition checking
                if "var" in condition:
                    var_path = condition["var"]
                    if var_path.startswith("state."):
                        path_parts = var_path.split(".")[1:]
                        value = state
                        for part in path_parts:
                            if part.startswith("[") and part.endswith("]"):
                                # Array access
                                index = int(part[1:-1])
                                value = value[index]
                            else:
                                value = value.get(part)
                        
                        # Check if value meets condition
                        if "==" in condition:
                            return value == condition["=="][1]
                        elif "<" in condition:
                            return value < condition["<"][1]
                        elif ">" in condition:
                            return value > condition[">"][1]
            
            return False
        except Exception:
            return False
    
    def _should_trigger_event(self, event, state: Dict[str, Any]) -> bool:
        """Check if an event should trigger"""
        
        # Simplified event triggering - in production, use proper JSONLogic evaluator
        try:
            # Check event condition
            if event.when:
                # Simple condition checking
                if "var" in event.when:
                    var_path = event.when["var"]
                    if var_path.startswith("state."):
                        path_parts = var_path.split(".")[1:]
                        value = state
                        for part in path_parts:
                            if part.startswith("[") and part.endswith("]"):
                                index = int(part[1:-1])
                                value = value[index]
                            else:
                                value = value.get(part)
                        
                        # Check if value meets condition
                        if "==" in event.when:
                            return value == event.when["=="][1]
                        elif "<" in event.when:
                            return value < event.when["<"][1]
                        elif ">" in event.when:
                            return value > event.when[">"][1]
            
            # Roll for event occurrence
            return random.random() < event.weight
        except Exception:
            return False
    
    def _apply_event_effects(self, event, state: Dict[str, Any]):
        """Apply event effects to state"""
        
        # Simplified effect application - in production, implement proper state updates
        for effect in event.effects:
            if effect.op == "set":
                # Set value at path
                pass
            elif effect.op == "inc":
                # Increment value at path
                pass
            # ... other operations
    
    def _get_available_actions(self, actions: List, state: Dict[str, Any]) -> List:
        """Get actions that are available given current state"""
        
        available = []
        for action in actions:
            if self._check_action_preconditions(action, state):
                available.append(action)
        return available
    
    def _check_action_preconditions(self, action, state: Dict[str, Any]) -> bool:
        """Check if action preconditions are met"""
        
        # Simplified precondition checking - in production, use proper JSONLogic evaluator
        try:
            if action.preconditions:
                # Simple condition checking
                if "var" in action.preconditions:
                    var_path = action.preconditions["var"]
                    if var_path.startswith("state."):
                        path_parts = var_path.split(".")[1:]
                        value = state
                        for part in path_parts:
                            if part.startswith("[") and part.endswith("]"):
                                index = int(part[1:-1])
                                value = value[index]
                            else:
                                value = value.get(part)
                        
                        # Check if value meets condition
                        if "==" in action.preconditions:
                            return value == action.preconditions["=="][1]
                        elif "<" in action.preconditions:
                            return value < action.preconditions["<"][1]
                        elif ">" in action.preconditions:
                            return value > action.preconditions[">"][1]
            
            return True  # Default to available if no preconditions
        except Exception:
            return False
    
    def _apply_action_effects(self, action, state: Dict[str, Any]):
        """Apply action effects to state"""
        
        # Simplified effect application - in production, implement proper state updates
        for effect in action.effects:
            if effect.op == "set":
                # Set value at path
                pass
            elif effect.op == "inc":
                # Increment value at path
                pass
            # ... other operations
