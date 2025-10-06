"""
Scenario compiler - converts specs to executable tools
"""

from typing import Dict, Any, List
from langchain.tools import BaseTool
from ..schemas import ScenarioSpec, Action


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
            name = action.id
            description = f"Action: {action.id}"
            
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
                # Simplified validation - in production, use proper JSON schema validation
                return True
            
            def _check_preconditions(self, preconditions: Dict[str, Any]) -> bool:
                """Check action preconditions"""
                # Simplified precondition checking - in production, use JSONLogic evaluator
                return True
            
            def _execute_effects(self, effects: List[Dict[str, Any]]) -> str:
                """Execute action effects"""
                # Simplified effect execution - in production, implement proper state updates
                return "Effects applied"
        
        return ActionTool()
    
    def get_tools(self) -> List[BaseTool]:
        """Get compiled tools"""
        return self.tools
