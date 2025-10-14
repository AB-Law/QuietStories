#!/usr/bin/env python3
"""
Test script to verify LMStudio and optimization setup.

This script checks:
1. LMStudio connection
2. Optimization configuration
3. Basic workflow functionality

Usage:
    python test_lmstudio_setup.py
"""

import asyncio
import os
import sys

import requests


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_env_vars():
    """Check if required environment variables are set."""
    print_section("1. Checking Environment Variables")

    required_vars = {
        "MODEL_PROVIDER": "Which LLM provider to use",
        "OPENAI_API_BASE": "LLM API endpoint",
        "MODEL_NAME": "Model name",
    }

    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var} = {value}")
        else:
            print(f"✗ {var} is not set ({description})")
            all_set = False

    return all_set


def check_backend_running(base_url="http://localhost:8000"):
    """Check if the backend server is running."""
    print_section("2. Checking Backend Server")

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Backend is running at {base_url}")
            return True
        else:
            print(f"✗ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to backend at {base_url}")
        print("  → Make sure to run: python -m uvicorn backend.main:app --reload")
        return False
    except Exception as e:
        print(f"✗ Error checking backend: {e}")
        return False


def check_lmstudio_connection():
    """Check if LMStudio is accessible."""
    print_section("3. Checking LMStudio Connection")

    provider = os.getenv("MODEL_PROVIDER", "").lower()
    api_base = os.getenv("OPENAI_API_BASE", "http://localhost:5101/v1")

    if provider != "lmstudio":
        print(f"  Skipping LMStudio check (provider is '{provider}')")
        return True

    try:
        # Try to list models endpoint
        models_url = api_base.replace("/v1", "/v1/models")
        response = requests.get(models_url, timeout=5)

        if response.status_code == 200:
            print(f"✓ LMStudio is running at {api_base}")
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                print(f"  → Models loaded: {len(data['data'])}")
            return True
        else:
            print(f"✗ LMStudio returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to LMStudio at {api_base}")
        print("  → Make sure LMStudio is running and server is started")
        print("  → Check port number in .env matches LMStudio")
        return False
    except Exception as e:
        print(f"✗ Error checking LMStudio: {e}")
        return False


def check_optimization_config(base_url="http://localhost:8000"):
    """Check optimization configuration."""
    print_section("4. Checking Optimization Configuration")

    try:
        response = requests.get(f"{base_url}/optimization/config", timeout=5)

        if response.status_code == 200:
            config = response.json()
            print("✓ Optimization is configured:")
            print(f"  → Max turn history: {config['max_turn_history']}")
            print(f"  → Max memories per entity: {config['max_memories_per_entity']}")
            print(f"  → Max context tokens: {config['max_context_tokens']}")
            print(f"  → Caching enabled: {config['enable_caching']}")
            return True
        else:
            print(f"✗ Failed to get optimization config: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error checking optimization: {e}")
        return False


def check_optimization_stats(base_url="http://localhost:8000"):
    """Check optimization statistics."""
    print_section("5. Checking Optimization Statistics")

    try:
        response = requests.get(f"{base_url}/optimization/stats", timeout=5)

        if response.status_code == 200:
            stats = response.json()
            cache_stats = stats.get("cache_stats", {})
            print("✓ Optimization statistics available:")
            print(f"  → Cache size: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}")
            print(f"  → Total cache accesses: {cache_stats.get('total_accesses', 0)}")
            return True
        else:
            print(f"✗ Failed to get stats: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error checking stats: {e}")
        return False


def list_presets(base_url="http://localhost:8000"):
    """List available optimization presets."""
    print_section("6. Available Optimization Presets")

    try:
        response = requests.get(f"{base_url}/optimization/presets", timeout=5)

        if response.status_code == 200:
            presets = response.json()
            print("✓ Available presets:")
            for name, config in presets.items():
                print(f"\n  {name}:")
                print(f"    Description: {config['description']}")
                print(f"    Max turn history: {config['max_turn_history']}")
                print(f"    Max context tokens: {config['max_context_tokens']}")
            return True
        else:
            print(f"✗ Failed to get presets: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error getting presets: {e}")
        return False


def suggest_preset():
    """Suggest an appropriate preset based on provider."""
    print_section("7. Recommended Configuration")

    provider = os.getenv("MODEL_PROVIDER", "").lower()

    if provider == "lmstudio" or provider == "ollama":
        print("📌 Recommended preset: local_llm")
        print("\nTo apply:")
        print("  curl -X POST http://localhost:8000/optimization/presets/local_llm")
    elif provider == "openai":
        print("📌 Recommended preset: cloud_llm")
        print("\nTo apply:")
        print("  curl -X POST http://localhost:8000/optimization/presets/cloud_llm")
    else:
        print("📌 Current provider:", provider or "not set")
        print("  See OPTIMIZATION_GUIDE.md for recommendations")


def main():
    """Run all checks."""
    print("\n" + "🎮" * 30)
    print(" QuietStories - LMStudio & Optimization Setup Test")
    print("🎮" * 30)

    # Run checks
    checks = [
        check_env_vars(),
        check_backend_running(),
        check_lmstudio_connection(),
        check_optimization_config(),
        check_optimization_stats(),
        list_presets(),
    ]

    # Suggest preset
    suggest_preset()

    # Summary
    print_section("Summary")

    passed = sum(checks)
    total = len(checks)

    if passed == total:
        print(f"✅ All checks passed! ({passed}/{total})")
        print("\nYour setup is ready to use.")
        print("See OPTIMIZATION_GUIDE.md for usage examples.")
        return 0
    else:
        print(f"⚠️  Some checks failed ({passed}/{total} passed)")
        print("\nPlease address the issues above.")
        print("See OPTIMIZATION_GUIDE.md for troubleshooting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

