"""
Schema validation utilities
"""

import json
from typing import Any, Dict, List, Optional
from jsonschema import validate, ValidationError
from .scenario import ScenarioSpec
from .outcome import Outcome


def validate_scenario_spec(spec_data: Dict[str, Any]) -> ScenarioSpec:
    """Validate and parse a scenario specification"""
    try:
        # Create ScenarioSpec instance (Pydantic validation)
        spec = ScenarioSpec(**spec_data)
        return spec
    except Exception as e:
        raise ValueError(f"Invalid scenario spec: {e}")


def validate_outcome(outcome_data: Dict[str, Any]) -> Outcome:
    """Validate and parse an outcome"""
    try:
        # Create Outcome instance (Pydantic validation)
        outcome = Outcome(**outcome_data)
        return outcome
    except Exception as e:
        raise ValueError(f"Invalid outcome: {e}")


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate data against a JSON schema"""
    try:
        validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        raise ValueError(f"JSON schema validation failed: {e}")


def validate_no_scenario_nouns(text: str, forbidden_nouns: List[str] = None) -> bool:
    """Validate that text contains no forbidden scenario nouns"""
    if forbidden_nouns is None:
        forbidden_nouns = []  # Empty list by default
    
    text_lower = text.lower()
    for noun in forbidden_nouns:
        if noun.lower() in text_lower:
            raise ValueError(f"Forbidden scenario noun found: {noun}")
    
    return True
