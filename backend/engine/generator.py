"""
Scenario generator — converts a free-text description into a ScenarioSpec v2.0.
"""

import json
import random
import re
from typing import Any, Dict

from langchain.schema import HumanMessage, SystemMessage

from backend.prompts import GENERATOR_SYSTEM, GENERATOR_USER
from backend.providers import create_provider
from backend.schemas import ScenarioSpec, validate_scenario_spec
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 2


class ScenarioGenerator:
    """Generates a ScenarioSpec from a free-text description."""

    def __init__(self):
        self.provider = create_provider()

    async def generate_scenario(self, description: str) -> ScenarioSpec:
        """Generate a ScenarioSpec from a free-text description."""
        messages = [
            SystemMessage(content=GENERATOR_SYSTEM),
            HumanMessage(content=GENERATOR_USER.format(description=description)),
        ]

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self.provider.chat(messages)
                raw = response.content

                spec_data = self._extract_json(raw)
                scenario_spec = validate_scenario_spec(spec_data)

                # Ensure seed is set
                if not scenario_spec.seed:
                    scenario_spec.seed = random.randint(1, 1_000_000)

                logger.info(
                    f"Scenario generated: '{scenario_spec.name}' "
                    f"({len(scenario_spec.actors)} actors) on attempt {attempt + 1}"
                )
                return scenario_spec

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Generation attempt {attempt + 1} failed: {type(e).__name__}: {e}"
                )
                if attempt < _MAX_RETRIES:
                    # Append the error and ask the LLM to self-correct
                    messages.append(
                        HumanMessage(
                            content=f"That response failed validation: {e}\n\n"
                            "Please fix it and return ONLY valid JSON."
                        )
                    )

        raise Exception(
            f"Scenario generation failed after {_MAX_RETRIES + 1} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Strip markdown fences and extract the outermost JSON object."""
        text = text.strip()

        # Remove ```json ... ``` or ``` ... ``` fences
        fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()

        # Find outermost braces
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in LLM response")

        return json.loads(text[start:end])
