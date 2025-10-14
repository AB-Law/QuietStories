"""
JSONLogic evaluator for conditions and derived values
"""

from typing import Any, Dict

import json_logic as jsonlogic


class JSONLogicEvaluator:
    """Evaluates JSONLogic expressions against state"""

    def __init__(self):
        self.evaluator = jsonlogic

    def evaluate(self, expression: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Evaluate a JSONLogic expression against context"""

        try:
            return self.evaluator.jsonLogic(expression, context)
        except Exception as e:
            raise ValueError(f"JSONLogic evaluation failed: {e}")

    def evaluate_condition(
        self, condition: Dict[str, Any], state: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition and return boolean result"""

        result = self.evaluate(condition, state)
        return bool(result)

    def evaluate_derived(
        self, derived_expr: Dict[str, Any], state: Dict[str, Any]
    ) -> Any:
        """Evaluate a derived value expression"""

        return self.evaluate(derived_expr, state)

    def validate_expression(self, expression: Dict[str, Any]) -> bool:
        """Validate that an expression is well-formed JSONLogic"""

        try:
            # Check if expression has valid JSONLogic structure
            if not isinstance(expression, dict):
                return False

            # Check for valid operators
            valid_operators = {
                "==",
                "!=",
                "<",
                ">",
                "<=",
                ">=",
                "and",
                "or",
                "not",
                "in",
                "cat",
                "+",
                "-",
                "*",
                "/",
                "%",
                "if",
                "var",
            }

            # Check if any key is a valid operator
            has_valid_operator = any(
                key in valid_operators for key in expression.keys()
            )
            if not has_valid_operator:
                return False

            # Try to evaluate with a test context
            test_context = {"test": True, "value": 1}
            self.evaluator.jsonLogic(expression, test_context)
            return True
        except Exception:
            return False
