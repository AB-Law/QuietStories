#!/usr/bin/env python3
"""
API Testing Script for QuietStories

This script makes HTTP requests to your running FastAPI server to test the APIs.

Prerequisites:
    1. Start the FastAPI server first:
       python -m uvicorn src.main:app --reload
    
    2. Or in debug mode in VSCode (F5)

Usage:
    # Set log level (DEBUG, INFO, WARNING, ERROR)
    python api_test.py --log-level DEBUG
    
    # Test prompt enrichment
    python api_test.py enrich "A detective mystery in 1920s New York"
    
    # Test scenario generation
    python api_test.py generate "A space adventure on Mars"
    
    # Test full workflow
    python api_test.py workflow "A fantasy quest with dragons"
    
    # List available scenarios
    python api_test.py list-scenarios
    
    # List available sessions
    python api_test.py list-sessions
    
    # Get specific scenario
    python api_test.py get-scenario <scenario_id>
    
    # Create session from scenario
    python api_test.py create-session <scenario_id>
    
    # Process a turn
    python api_test.py process-turn <session_id> --action "look around"
"""

import asyncio
import argparse
import sys
import json
import httpx
from typing import Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


class APITester:
    """Helper class for testing API endpoints via HTTP"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.logger = get_logger(self.__class__.__name__)
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def check_server(self):
        """Check if server is running"""
        try:
            response = await self.client.get("/health")
            if response.status_code == 200:
                self.logger.info(f"✓ Server is running at {self.base_url}")
                return True
            else:
                self.logger.error(f"✗ Server returned status {response.status_code}")
                return False
        except httpx.ConnectError:
            self.logger.error(f"✗ Cannot connect to server at {self.base_url}")
            self.logger.error("Please start the server first:")
            self.logger.error("  python -m uvicorn src.main:app --reload")
            return False
        except Exception as e:
            self.logger.error(f"✗ Error checking server: {e}")
            return False
    
    async def test_enrich_prompt(self, description: str, max_tokens: int = 500):
        """Test prompt enrichment"""
        self.logger.info(f"Testing prompt enrichment for: {description[:50]}...")
        
        payload = {
            "description": description,
            "max_tokens": max_tokens
        }
        
        try:
            response = await self.client.post("/prompts/enrich", json=payload)
            response.raise_for_status()
            result = response.json()
            
            self.logger.info("✓ Prompt enrichment successful")
            print("\n" + "="*80)
            print("ORIGINAL PROMPT:")
            print("-"*80)
            print(result['original'])
            print("\n" + "="*80)
            print("ENRICHED PROMPT:")
            print("-"*80)
            print(result['enriched'])
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Prompt enrichment failed: {e}", exc_info=True)
            raise
    
    async def test_generate_scenario(self, description: str):
        """Test scenario generation"""
        self.logger.info(f"Testing scenario generation for: {description[:50]}...")
        
        payload = {"description": description}
        
        try:
            response = await self.client.post("/scenarios/generate", json=payload)
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"✓ Scenario generation successful: {result['name']}")
            print("\n" + "="*80)
            print("GENERATED SCENARIO:")
            print("-"*80)
            print(f"ID: {result['id']}")
            print(f"Name: {result['name']}")
            print(f"Spec Version: {result['spec_version']}")
            print(f"Status: {result['status']}")
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Scenario generation failed: {e}", exc_info=True)
            raise
    
    async def test_compile_scenario(self, scenario_id: str):
        """Test scenario compilation"""
        self.logger.info(f"Testing scenario compilation for: {scenario_id}")
        
        try:
            response = await self.client.post(f"/scenarios/{scenario_id}/compile")
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"✓ Scenario compilation successful")
            print("\n" + "="*80)
            print("COMPILATION RESULT:")
            print("-"*80)
            print(f"ID: {result['id']}")
            print(f"Status: {result['status']}")
            print(f"Validation Results:")
            print(json.dumps(result['validation_results'], indent=2))
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Scenario compilation failed: {e}", exc_info=True)
            raise
    
    async def test_create_session(self, scenario_id: str, seed: Optional[int] = None):
        """Test session creation"""
        self.logger.info(f"Testing session creation for scenario: {scenario_id}")
        
        payload = {"scenario_id": scenario_id}
        if seed is not None:
            payload["seed"] = seed
        
        try:
            response = await self.client.post("/sessions/", json=payload)
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"✓ Session creation successful: {result['id']}")
            print("\n" + "="*80)
            print("CREATED SESSION:")
            print("-"*80)
            print(f"Session ID: {result['id']}")
            print(f"Scenario ID: {result['scenario_id']}")
            print(f"Status: {result['status']}")
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Session creation failed: {e}", exc_info=True)
            raise
    
    async def test_process_turn(self, session_id: str, action: Optional[str] = None):
        """Test turn processing"""
        self.logger.info(f"Testing turn processing for session: {session_id}")
        
        payload = {"action": action, "parameters": {}}
        
        try:
            response = await self.client.post(f"/sessions/{session_id}/turns", json=payload)
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"✓ Turn processing successful")
            print("\n" + "="*80)
            print("TURN RESULT:")
            print("-"*80)
            print(f"Session ID: {result['session_id']}")
            print(f"Turn: {result['turn']}")
            print(f"\nNarrative:")
            print(result['outcome']['narrative'])
            print(f"\nState Changes: {len(result['outcome']['state_changes'])} changes")
            for change in result['outcome']['state_changes']:
                print(f"  - {change['op']} {change['path']} = {change['value']}")
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Turn processing failed: {e}", exc_info=True)
            raise
    
    async def test_full_workflow(self, description: str):
        """Test the complete workflow: enrich -> generate -> compile -> session -> turn"""
        self.logger.info("="*80)
        self.logger.info("STARTING FULL WORKFLOW TEST")
        self.logger.info("="*80)
        
        try:
            # Step 1: Enrich prompt
            self.logger.info("\n[1/5] Enriching prompt...")
            enriched = await self.test_enrich_prompt(description)
            
            # Step 2: Generate scenario
            self.logger.info("\n[2/5] Generating scenario...")
            scenario = await self.test_generate_scenario(enriched['enriched'])
            
            # Step 3: Compile scenario
            self.logger.info("\n[3/5] Compiling scenario...")
            compiled = await self.test_compile_scenario(scenario['id'])
            
            if compiled['status'] != "compiled":
                self.logger.error("Scenario compilation failed, stopping workflow")
                return
            
            # Step 4: Create session
            self.logger.info("\n[4/5] Creating session...")
            session = await self.test_create_session(scenario['id'])
            
            # Step 5: Process first turn
            self.logger.info("\n[5/5] Processing first turn...")
            turn_result = await self.test_process_turn(session['id'])
            
            self.logger.info("="*80)
            self.logger.info("✓ FULL WORKFLOW COMPLETED SUCCESSFULLY")
            self.logger.info("="*80)
            
            return {
                "enriched": enriched,
                "scenario": scenario,
                "compiled": compiled,
                "session": session,
                "turn_result": turn_result
            }
            
        except Exception as e:
            self.logger.error(f"✗ Full workflow failed: {e}", exc_info=True)
            raise
    
    async def test_list_scenarios(self):
        """List all scenarios"""
        self.logger.info("Listing all scenarios...")
        
        try:
            response = await self.client.get("/scenarios/")
            response.raise_for_status()
            result = response.json()
            
            print("\n" + "="*80)
            print(f"SCENARIOS ({len(result['scenarios'])} total):")
            print("-"*80)
            for scenario in result['scenarios']:
                print(f"  - {scenario['id']}: {scenario['name']} ({scenario['status']})")
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ List scenarios failed: {e}", exc_info=True)
            raise
    
    async def test_list_sessions(self):
        """List all sessions"""
        self.logger.info("Listing all sessions...")
        
        try:
            response = await self.client.get("/sessions/")
            response.raise_for_status()
            result = response.json()
            
            print("\n" + "="*80)
            print(f"SESSIONS ({len(result['sessions'])} total):")
            print("-"*80)
            for session in result['sessions']:
                print(f"  - {session['id']}: Scenario {session['scenario_id']}, Turn {session['turn']} ({session['status']})")
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ List sessions failed: {e}", exc_info=True)
            raise
    
    async def test_get_scenario(self, scenario_id: str):
        """Get a specific scenario"""
        self.logger.info(f"Getting scenario: {scenario_id}")
        
        try:
            response = await self.client.get(f"/scenarios/{scenario_id}")
            response.raise_for_status()
            result = response.json()
            
            print("\n" + "="*80)
            print("SCENARIO DETAILS:")
            print("-"*80)
            print(json.dumps(result, indent=2, default=str))
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Get scenario failed: {e}", exc_info=True)
            raise
    
    async def test_get_session(self, session_id: str):
        """Get a specific session"""
        self.logger.info(f"Getting session: {session_id}")
        
        try:
            response = await self.client.get(f"/sessions/{session_id}")
            response.raise_for_status()
            result = response.json()
            
            print("\n" + "="*80)
            print("SESSION DETAILS:")
            print("-"*80)
            print(json.dumps(result, indent=2, default=str))
            print("="*80 + "\n")
            return result
        except httpx.HTTPStatusError as e:
            self.logger.error(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Get session failed: {e}", exc_info=True)
            raise


async def main():
    parser = argparse.ArgumentParser(
        description="Test QuietStories API endpoints via HTTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "command",
        choices=[
            "enrich", "generate", "compile", "create-session", 
            "process-turn", "workflow", "list-scenarios", "list-sessions",
            "get-scenario", "get-session"
        ],
        help="Command to execute"
    )
    
    parser.add_argument(
        "arg",
        nargs="?",
        help="Argument for the command (description, scenario_id, or session_id)"
    )
    
    parser.add_argument(
        "--action",
        help="Action to take for process-turn command"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=500,
        help="Max tokens for enrichment (default: 500)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed for session creation"
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API server (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Optional log file path"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(
        level=args.log_level,
        log_file=args.log_file,
        enable_colors=True,
        include_timestamp=True
    )
    
    # Display configuration
    logger.info("="*80)
    logger.info("QuietStories API Tester (HTTP Mode)")
    logger.info("="*80)
    logger.info(f"API Server: {args.url}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("="*80)
    
    # Execute command with context manager
    async with APITester(base_url=args.url) as tester:
        # Check server first
        if not await tester.check_server():
            logger.error("\nPlease start the FastAPI server first:")
            logger.error("  python -m uvicorn src.main:app --reload")
            logger.error("  Or press F5 in VSCode to start in debug mode")
            sys.exit(1)
        
        try:
            if args.command == "enrich":
                if not args.arg:
                    parser.error("enrich requires a description argument")
                await tester.test_enrich_prompt(args.arg, args.max_tokens)
            
            elif args.command == "generate":
                if not args.arg:
                    parser.error("generate requires a description argument")
                await tester.test_generate_scenario(args.arg)
            
            elif args.command == "compile":
                if not args.arg:
                    parser.error("compile requires a scenario_id argument")
                await tester.test_compile_scenario(args.arg)
            
            elif args.command == "create-session":
                if not args.arg:
                    parser.error("create-session requires a scenario_id argument")
                await tester.test_create_session(args.arg, args.seed)
            
            elif args.command == "process-turn":
                if not args.arg:
                    parser.error("process-turn requires a session_id argument")
                await tester.test_process_turn(args.arg, args.action)
            
            elif args.command == "workflow":
                if not args.arg:
                    parser.error("workflow requires a description argument")
                await tester.test_full_workflow(args.arg)
            
            elif args.command == "list-scenarios":
                await tester.test_list_scenarios()
            
            elif args.command == "list-sessions":
                await tester.test_list_sessions()
            
            elif args.command == "get-scenario":
                if not args.arg:
                    parser.error("get-scenario requires a scenario_id argument")
                await tester.test_get_scenario(args.arg)
            
            elif args.command == "get-session":
                if not args.arg:
                    parser.error("get-session requires a session_id argument")
                await tester.test_get_session(args.arg)
            
            logger.info("\n✓ Test completed successfully")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"\n✗ Test failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
