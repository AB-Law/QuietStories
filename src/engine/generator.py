"""
Scenario generator using LLM to create dynamic scenarios from free text
"""

import json
import random
from typing import Dict, Any, List
from langchain.schema import SystemMessage, HumanMessage
from src.providers import create_provider
from src.schemas import ScenarioSpec, validate_scenario_spec


class ScenarioGenerator:
    """Generates dynamic scenarios from free-text descriptions"""
    
    def __init__(self):
        self.provider = create_provider()
    
    async def generate_scenario(self, description: str) -> ScenarioSpec:
        """Generate a scenario specification from free-text description"""
        
        # System prompt for scenario generation
        system_prompt = """You produce a ScenarioSpec that matches a provided jsonschema and uses ONLY the allowed effect operations.
Include at least TWO loss_conditions and a non-zero negativity_budget.
Provide a random_events deck where each event's weight is within allowed bounds.
Use JSONLogic only in preconditions and derives.
Do not include narrative prose or extra keys. Output ONLY the ScenarioSpec.

The ScenarioSpec must include:
- spec_version: "1.0"
- id: unique string identifier
- name: descriptive name
- seed: random integer
- state: initial state object
- entities: array of entity definitions
- actions: array of action definitions with preconditions and effects
- random_events: array of random events with weights 0.05-0.30
- loss_conditions: at least 2 loss conditions
- negativity_budget: with min_fail_rate > 0

Effect operations allowed: set, inc, dec, mul, patch, push, pop, addlog
Paths use JSON pointer format: state.a.b[2].c
"""
        
        # User prompt with the description
        user_prompt = f"""Create a dynamic scenario based on this description:

{description}

Generate a complete ScenarioSpec JSON that can be used for an interactive story. Make it challenging but fair, with multiple paths to success and failure."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            # Get response from LLM
            response = await self.provider.chat(messages)
            content = response.content
            
            # Try to parse JSON
            try:
                spec_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx:end_idx]
                    spec_data = json.loads(json_str)
                else:
                    raise ValueError("No valid JSON found in response")
            
            # Validate the scenario spec
            scenario_spec = validate_scenario_spec(spec_data)
            
            # Ensure we have a valid seed
            if not scenario_spec.seed:
                scenario_spec.seed = random.randint(1, 1000000)
            
            return scenario_spec
            
        except Exception as e:
            raise Exception(f"Failed to generate scenario: {e}")
    
    async def repair_scenario(self, spec_data: Dict[str, Any], issues: List[str]) -> ScenarioSpec:
        """Repair a scenario specification based on validation issues"""
        
        repair_prompt = f"""The following scenario specification has validation issues:

Issues: {', '.join(issues)}

Scenario: {json.dumps(spec_data, indent=2)}

Please fix these issues and return a corrected ScenarioSpec JSON. Ensure all requirements are met:
- At least 2 loss conditions
- Non-zero negativity budget
- Valid effect operations only
- Random event weights between 0.05-0.30
- Valid JSONLogic in preconditions and derives
"""
        
        messages = [
            SystemMessage(content="You are a scenario specification repair expert. Fix validation issues and return valid JSON only."),
            HumanMessage(content=repair_prompt)
        ]
        
        try:
            response = await self.provider.chat(messages)
            content = response.content
            
            # Extract and parse JSON
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                repaired_data = json.loads(json_str)
                return validate_scenario_spec(repaired_data)
            else:
                raise ValueError("No valid JSON found in repair response")
                
        except Exception as e:
            raise Exception(f"Failed to repair scenario: {e}")
