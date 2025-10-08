"""
Scenario compiler - converts specs to executable tools
"""

from typing import Dict, Any, List
from langchain.tools import BaseTool
from src.schemas import ScenarioSpec, Action
from src.utils.jsonlogic import JSONLogicEvaluator
from src.schemas.outcome import StateChange
from jsonschema import validate


class ScenarioCompiler:
    """Compiles scenario specifications into executable tools"""
    
    def __init__(self, spec: ScenarioSpec):
        self.spec = spec
        self.tools = []
        self._compile_actions()
    
    def _compile_actions(self):
        """Compile actions into LangChain tools"""
        
        for action in self.spec.actions:
            tool = self._create_action_tool(action)
            self.tools.append(tool)
    
    def _create_action_tool(self, action: Action) -> BaseTool:
        """Create a LangChain tool from an action"""
        
        class ActionTool(BaseTool):
            # Pydantic v2/LC tools require annotated fields
            name: str = action.id
            description: str = f"Action: {action.id}"
            
            def _run(self, **kwargs) -> str:
                """Execute the action"""
                # Validate parameters
                if not self._validate_params(action.params, kwargs):
                    return "Invalid parameters"
                
                # Check preconditions
                if not self._check_preconditions(action.preconditions):
                    return "Preconditions not met"
                
                # Execute effects
                result = self._execute_effects(action.effects)
                return f"Action {action.id} executed: {result}"
            
            def _validate_params(self, param_schema: Dict[str, Any], params: Dict[str, Any]) -> bool:
                """Validate action parameters"""
                try:
                    validate(instance=params, schema=param_schema)
                    return True
                except Exception:
                    return False
            
            def _check_preconditions(self, preconditions: Dict[str, Any]) -> bool:
                """Check action preconditions"""
                try:
                    evaluator = JSONLogicEvaluator()
                    # Get current state from the orchestrator
                    current_state = getattr(self, '_current_state', {})
                    return evaluator.evaluate_condition(preconditions, current_state)
                except Exception:
                    return False
            
            def _execute_effects(self, effects: List[Dict[str, Any]]) -> str:
                """Execute action effects"""
                try:
                    # Convert effects to StateChange objects and apply them
                    state_changes = [StateChange(**effect) for effect in effects]
                    # In production, this would update the actual game state
                    return f"Applied {len(state_changes)} effects"
                except Exception as e:
                    return f"Error applying effects: {e}"
        
        return ActionTool()
    
    def get_tools(self) -> List[BaseTool]:
        """Get compiled tools"""
        return self.tools
