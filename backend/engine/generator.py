"""
Scenario generator using LLM to create dynamic scenarios from free text
"""

import json
import random
from typing import Dict, Any, List
from langchain.schema import SystemMessage, HumanMessage
from backend.providers import create_provider
from backend.schemas import ScenarioSpec, validate_scenario_spec
from backend.prompts import SCENARIO_GENERATION_SYSTEM, SCENARIO_GENERATION_USER


class ScenarioGenerator:
    """Generates dynamic scenarios from free-text descriptions"""
    
    def __init__(self):
        self.provider = create_provider()
    
    async def generate_scenario(self, description: str) -> ScenarioSpec:
        """Generate a scenario specification from free-text description"""
        
        import logging
        logger = logging.getLogger(__name__)
        
        # Use prompts from prompts.py
        user_prompt = SCENARIO_GENERATION_USER.format(description=description)
        
        messages = [
            SystemMessage(content=SCENARIO_GENERATION_SYSTEM),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            # Use LangChain's structured output for reliable JSON generation
            # Ref: https://python.langchain.com/docs/concepts/structured_outputs/
            logger.info("Using structured output to generate ScenarioSpec...")
            llm = self.provider.llm
            structured_llm = llm.with_structured_output(ScenarioSpec, method="json_mode")
            logger.info("Invoking LLM with structured output...")
            scenario_spec = await structured_llm.ainvoke(messages)
            logger.info(f"Successfully generated scenario: {scenario_spec.name}")

            # Ensure we have a valid seed
            if not scenario_spec.seed:
                scenario_spec.seed = random.randint(1, 1000000)

            return scenario_spec

        except Exception as e:
            # Fallback: some providers (e.g., strict JSON mode) reject dynamic object fields
            # like Action.params/JSONLogic. Fall back to robust JSON parsing flow.
            logger.error(
                f"Structured output failed, falling back to manual parsing: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )

            # ---------- Fallback path: standard chat + robust JSON extraction ----------
            messages = [
                SystemMessage(content=SCENARIO_GENERATION_SYSTEM),
                HumanMessage(content=user_prompt),
            ]

            # Get response from LLM
            response = await self.provider.chat(messages)
            content = response.content

            import logging
            import re
            logger = logging.getLogger(__name__)
            logger.info(f"LLM response length: {len(content)}")
            logger.info(f"LLM response first 300 chars: {content[:300]}")

            # Clean the response - remove markdown code blocks and other formatting
            content = content.strip()

            # Remove markdown code blocks
            if '```' in content:
                # Extract content between code fences
                match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
                if match:
                    content = match.group(1)
                    logger.info("Extracted JSON from markdown code block")
                else:
                    # Fallback: remove all lines with ```
                    lines = [line for line in content.split('\n') if not line.strip().startswith('```')]
                    content = '\n'.join(lines)
                    logger.info("Removed markdown code fence lines")

            # Try to parse JSON
            try:
                spec_data = json.loads(content)
                logger.info("Successfully parsed JSON from fallback response")
            except json.JSONDecodeError as e2:
                logger.warning(f"Initial JSON parse failed in fallback: {e2}")
                # Try to extract JSON from response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    logger.info(f"Extracted JSON substring (length {len(json_str)}) in fallback")
                    spec_data = json.loads(json_str)
                    logger.info("Successfully parsed extracted JSON in fallback")
                else:
                    logger.error(f"No valid JSON found in fallback. Content: {content[:500]}")
                    raise Exception("No valid JSON found in LLM response")

            # Auto-fix common LLM mistakes with field names
            spec_data = self._fix_field_names(spec_data)

            # Validate the scenario spec
            scenario_spec = validate_scenario_spec(spec_data)

            # Ensure we have a valid seed
            if not scenario_spec.seed:
                scenario_spec.seed = random.randint(1, 1000000)

            return scenario_spec
    
    def _fix_field_names(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common LLM mistakes with field names"""
        
        # Fix actions
        if "actions" in spec_data:
            for action in spec_data["actions"]:
                # Add missing params
                if "params" not in action:
                    action["params"] = {}
                
                # Fix effects
                if "effects" in action:
                    for effect in action["effects"]:
                        if "operation" in effect and "op" not in effect:
                            effect["op"] = effect.pop("operation")
        
        # Fix random_events
        if "random_events" in spec_data:
            for event in spec_data["random_events"]:
                # Fix when field
                if "condition" in event and "when" not in event:
                    event["when"] = event.pop("condition")
                elif "when" not in event:
                    event["when"] = {}
                
                # Fix effects
                if "effects" in event:
                    for effect in event["effects"]:
                        if "operation" in effect and "op" not in effect:
                            effect["op"] = effect.pop("operation")
        
        # Fix loss_conditions
        if "loss_conditions" in spec_data:
            for condition in spec_data["loss_conditions"]:
                if "message" not in condition:
                    condition["message"] = condition.get("name", "You lost")
        
        # Fix negativity_budget
        if "negativity_budget" in spec_data:
            if "decay_per_turn" not in spec_data["negativity_budget"]:
                spec_data["negativity_budget"]["decay_per_turn"] = {}
        
        return spec_data
    
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
