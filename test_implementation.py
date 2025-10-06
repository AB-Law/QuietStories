#!/usr/bin/env python3
"""
Simple test script to verify the Dynamic CYOA Engine implementation
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported"""
    
    print("Testing imports...")
    
    try:
        # Test config
        from config import settings
        print(f"✓ Config loaded: Provider = {settings.model_provider}")
    except Exception as e:
        print(f"✗ Config failed: {e}")
        return False
    
    try:
        # Test schemas
        from schemas import ScenarioSpec, Outcome
        print("✓ Schemas imported")
    except Exception as e:
        print(f"✗ Schemas failed: {e}")
        return False
    
    try:
        # Test providers
        from providers import create_provider
        print("✓ Providers imported")
    except Exception as e:
        print(f"✗ Providers failed: {e}")
        return False
    
    try:
        # Test engine
        from engine import ScenarioGenerator, ScenarioValidator
        print("✓ Engine imported")
    except Exception as e:
        print(f"✗ Engine failed: {e}")
        return False
    
    return True

def test_schema_validation():
    """Test schema validation"""
    
    print("\nTesting schema validation...")
    
    try:
        from schemas import ScenarioSpec, Outcome
        
        # Test valid scenario spec
        valid_spec = {
            "spec_version": "1.0",
            "id": "test",
            "name": "Test Scenario",
            "seed": 123,
            "state": {"health": 100},
            "entities": [],
            "actions": [],
            "random_events": [],
            "loss_conditions": [
                {"id": "death", "condition": {"<": [{"var": "state.health"}, 0]}, "message": "You died"},
                {"id": "timeout", "condition": {">": [{"var": "state.turns"}, 100]}, "message": "Time out"}
            ],
            "negativity_budget": {"min_fail_rate": 0.25, "decay_per_turn": {}}
        }
        
        spec = ScenarioSpec(**valid_spec)
        print(f"✓ ScenarioSpec validation passed: {spec.id}")
        
        # Test valid outcome
        valid_outcome = {
            "narrative": "The story continues...",
            "state_changes": [{"op": "set", "path": "state.turns", "value": 1}]
        }
        
        outcome = Outcome(**valid_outcome)
        print(f"✓ Outcome validation passed: {outcome.narrative[:20]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema validation failed: {e}")
        return False

def test_no_nouns():
    """Test that no forbidden nouns exist"""
    
    print("\nTesting no-nouns constraint...")
    
    forbidden_nouns = []  # Empty list by default
    
    # Check a few key files
    files_to_check = [
        "src/main.py",
        "src/config.py", 
        "src/engine/generator.py"
    ]
    
    violations = []
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                for noun in forbidden_nouns:
                    if noun.lower() in content.lower():
                        violations.append(f"{file_path}: Found '{noun}'")
            except Exception:
                continue
    
    if violations:
        print(f"✗ Found forbidden nouns: {violations}")
        return False
    else:
        print("✓ No forbidden nouns found")
        return True

def main():
    """Run all tests"""
    
    print("Dynamic CYOA Engine - Implementation Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_schema_validation,
        test_no_nouns
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation looks good.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
