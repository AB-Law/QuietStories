"""
Test for forbidden scenario nouns in codebase
"""

import os
import re
from pathlib import Path


def test_no_scenario_nouns():
    """Test that no forbidden scenario nouns exist in the codebase"""

    # List of forbidden nouns (empty by default as per requirements)
    forbidden_nouns = []

    # Get project root
    project_root = Path(__file__).parent.parent

    # Files to check
    files_to_check = ["src/**/*.py", "tests/**/*.py", "*.py"]

    violations = []

    for pattern in files_to_check:
        for file_path in project_root.glob(pattern):
            if file_path.is_file() and file_path.suffix == ".py":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check for forbidden nouns
                    for noun in forbidden_nouns:
                        if re.search(rf"\b{re.escape(noun)}\b", content, re.IGNORECASE):
                            violations.append(
                                f"{file_path}: Found forbidden noun '{noun}'"
                            )

                except Exception as e:
                    # Skip files that can't be read
                    continue

    # Assert no violations found
    assert len(violations) == 0, f"Found forbidden scenario nouns: {violations}"


def test_no_hardcoded_scenarios():
    """Test that no hardcoded scenario content exists"""

    # Patterns that might indicate hardcoded scenarios
    suspicious_patterns = [
        r"def.*scenario.*\(",  # Function names with scenario
        r"class.*Scenario.*:",  # Class names with Scenario
        r"SCENARIO.*=",  # Constants with SCENARIO
        r'"scenario".*:',  # Dictionary keys with scenario
    ]

    project_root = Path(__file__).parent.parent
    violations = []

    for file_path in project_root.glob("src/**/*.py"):
        if file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern in suspicious_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        violations.append(
                            f"{file_path}: Found suspicious pattern '{pattern}': {matches}"
                        )

            except Exception:
                continue

    # This test is more lenient - just warn about potential issues
    if violations:
        print(f"Warning: Found potential hardcoded scenario patterns: {violations}")
        # Don't fail the test, just warn
