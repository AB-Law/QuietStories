"""
Scenario management API endpoints.

This module handles scenario generation, compilation, and validation.
Supports both legacy ScenarioSpec and simplified narrative-driven scenarios.
Scenarios are stored in SQLite via DatabaseManager for persistence.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.engine.generator import ScenarioGenerator
from backend.engine.simplified_generator import SimplifiedScenarioGenerator
from backend.engine.validator import ScenarioValidator
from backend.schemas import ScenarioSpec
from backend.schemas.simplified import (
    ScenarioGenerationRequest,
    ScenarioGenerationResponse,
    SimplifiedScenario,
)
from backend.utils.logger import get_logger

# Set up logging
logger = get_logger(__name__)

router = APIRouter()

# Database manager for persistent storage
db = DatabaseManager(settings.database_path)


class LegacyScenarioGenerateRequest(BaseModel):
    """Request to generate a legacy scenario (for backward compatibility)"""

    description: str


class LegacyScenarioGenerateResponse(BaseModel):
    """Response from legacy scenario generation"""

    id: str
    name: str
    spec_version: str
    status: str


class ScenarioCompileRequest(BaseModel):
    """Request to compile a scenario"""

    spec: Dict[str, Any]


class ScenarioCompileResponse(BaseModel):
    """Response from scenario compilation"""

    id: str
    status: str
    validation_results: Dict[str, Any]


@router.post("/generate", response_model=ScenarioGenerationResponse)
async def generate_scenario(
    request: ScenarioGenerationRequest,
    use_legacy: bool = Query(
        False, description="Use legacy ScenarioSpec generation (deprecated)"
    ),
):
    """
    Generate a new scenario from free-text description.

    By default, uses the simplified narrative-driven approach.
    Set use_legacy=true for backward compatibility with old ScenarioSpec format.
    """
    logger.info("=" * 60)
    logger.info(f"SCENARIO GENERATION REQUEST")
    logger.info(f"Description: {request.description[:100]}...")
    logger.info(f"Mode: {'legacy' if use_legacy else 'simplified'}")
    logger.debug(f"Full description: {request.description}")

    try:
        if use_legacy:
            # Use legacy ScenarioSpec generation for backward compatibility
            logger.info("Using legacy ScenarioSpec generation")
            return await _generate_legacy_scenario(request.description)
        else:
            # Use new simplified generation (default)
            logger.info("Using simplified narrative-driven generation")
            return await _generate_simplified_scenario(request)

    except Exception as e:
        logger.error(f"✗ Scenario generation failed")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate scenario: {type(e).__name__}: {str(e)}",
        )


async def _generate_simplified_scenario(
    request: ScenarioGenerationRequest,
) -> ScenarioGenerationResponse:
    """Generate a simplified scenario (new default approach)."""
    logger.debug("Initializing SimplifiedScenarioGenerator...")
    generator = SimplifiedScenarioGenerator()

    logger.info("Starting simplified scenario generation...")
    scenario = await generator.generate_scenario(
        description=request.description,
        num_characters=request.num_characters,
        include_player=request.include_player,
        player_name=request.player_name,
        difficulty=request.difficulty,
    )

    logger.info(f"✓ Simplified scenario generated: {scenario.name}")
    logger.debug(f"Characters: {len(scenario.characters)}")
    logger.debug(f"Themes: {', '.join(scenario.world_background.themes)}")

    # Store the scenario in database with type marker
    scenario_data = {
        "id": scenario.id,
        "name": scenario.name,
        "spec": {
            "type": "simplified",
            "data": scenario.dict(),
        },
        "status": "generated",
    }
    db.save_scenario(scenario_data)
    logger.info(f"Simplified scenario stored with ID: {scenario.id}")

    return ScenarioGenerationResponse(
        id=scenario.id,
        name=scenario.name,
        status="generated",
        character_count=len(scenario.characters),
        has_world_background=True,
    )


async def _generate_legacy_scenario(description: str) -> ScenarioGenerationResponse:
    """Generate a legacy ScenarioSpec (deprecated, for backward compatibility)."""
    logger.debug("Initializing legacy ScenarioGenerator...")
    generator = ScenarioGenerator()

    logger.info("Starting legacy scenario generation...")
    scenario_spec = await generator.generate_scenario(description)

    logger.info(f"✓ Legacy scenario generated: {scenario_spec.name}")
    logger.debug(f"Spec version: {scenario_spec.spec_version}")

    # Store with legacy type marker
    scenario_id = str(uuid.uuid4())
    scenario_data = {
        "id": scenario_id,
        "name": scenario_spec.name,
        "spec": {
            "type": "legacy",
            "data": scenario_spec.dict(),
        },
        "status": "generated",
    }
    db.save_scenario(scenario_data)
    logger.info(f"Legacy scenario stored with ID: {scenario_id}")

    return ScenarioGenerationResponse(
        id=scenario_id,
        name=scenario_spec.name,
        status="generated",
        character_count=len(scenario_spec.entities) if scenario_spec.entities else 0,
        has_world_background=False,
    )


@router.post("/{scenario_id}/compile", response_model=ScenarioCompileResponse)
async def compile_scenario(scenario_id: str):
    """
    Validate and compile a scenario specification.

    For simplified scenarios, this just validates the structure.
    For legacy ScenarioSpec scenarios, runs full validation and Monte Carlo.
    """
    logger.info("=" * 60)
    logger.info(f"SCENARIO COMPILATION REQUEST")
    logger.info(f"Scenario ID: {scenario_id}")

    # Get scenario from database
    scenario = db.get_scenario(scenario_id)
    if not scenario:
        logger.warning(f"✗ Scenario not found: {scenario_id}")
        raise HTTPException(status_code=404, detail="Scenario not found")

    try:
        spec_dict = scenario["spec"]

        # Check if this is a simplified or legacy scenario
        is_simplified = spec_dict.get("type") == "simplified"

        if is_simplified:
            logger.info("Compiling simplified scenario (structure validation only)")
            return await _compile_simplified_scenario(scenario_id, spec_dict)
        else:
            logger.info("Compiling legacy ScenarioSpec (full validation + Monte Carlo)")
            return await _compile_legacy_scenario(scenario_id, spec_dict)

    except Exception as e:
        logger.error(f"✗ Compilation failed")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to compile scenario: {type(e).__name__}: {str(e)}",
        )


async def _compile_simplified_scenario(
    scenario_id: str, spec_dict: Dict[str, Any]
) -> ScenarioCompileResponse:
    """Compile a simplified scenario (just structural validation)."""
    data = spec_dict.get("data", {})
    scenario_name = data.get("name", "Unknown")

    logger.info(f"Validating simplified scenario: {scenario_name}")

    try:
        # Validate by attempting to parse as SimplifiedScenario
        SimplifiedScenario(**data)
        logger.info("✓ Simplified scenario structure is valid")

        # Update scenario status
        db.update_scenario_status(scenario_id, "compiled")
        logger.info(f"✓ Simplified scenario compiled successfully: {scenario_id}")

        return ScenarioCompileResponse(
            id=scenario_id,
            status="compiled",
            validation_results={
                "valid": True,
                "type": "simplified",
                "monte_carlo_skipped": True,
                "message": "Simplified scenarios don't require Monte Carlo validation",
            },
        )

    except Exception as e:
        logger.error(f"✗ Simplified scenario validation failed: {e}")
        return ScenarioCompileResponse(
            id=scenario_id,
            status="failed",
            validation_results={
                "valid": False,
                "type": "simplified",
                "error": str(e),
            },
        )


async def _compile_legacy_scenario(
    scenario_id: str, spec_dict: Dict[str, Any]
) -> ScenarioCompileResponse:
    """Compile a legacy ScenarioSpec (full validation + Monte Carlo)."""
    # Extract the actual spec data (handle both wrapped and unwrapped formats)
    if spec_dict.get("type") == "legacy":
        actual_spec = spec_dict.get("data", {})
    else:
        actual_spec = spec_dict

    scenario_name = actual_spec.get("name", "Unknown")
    logger.info(f"Validating legacy ScenarioSpec: {scenario_name}")

    logger.debug("Initializing ScenarioValidator...")
    validator = ScenarioValidator()

    # Validate the spec
    logger.info("Validating scenario specification...")
    is_valid, issues = validator.validate_spec(actual_spec)

    if not is_valid:
        logger.warning(f"⚠ Spec validation failed with {len(issues)} issues")
        for i, issue in enumerate(issues[:5], 1):
            logger.warning(f"  Issue {i}: {issue}")
        if len(issues) > 5:
            logger.warning(f"  ... and {len(issues) - 5} more issues")

        # Try auto-repair
        logger.info("Attempting auto-repair...")
        repaired_spec = validator.auto_repair(actual_spec, issues)
        is_valid, issues = validator.validate_spec(repaired_spec)

        if not is_valid:
            logger.error(f"✗ Auto-repair failed. {len(issues)} remaining issues")
            for i, issue in enumerate(issues[:3], 1):
                logger.error(f"  Issue {i}: {issue}")
            return ScenarioCompileResponse(
                id=scenario_id,
                status="failed",
                validation_results={
                    "valid": False,
                    "type": "legacy",
                    "issues": issues,
                    "auto_repair_attempted": True,
                },
            )
        # Use repaired spec
        actual_spec = repaired_spec
        logger.info("✓ Auto-repair successful")
    else:
        logger.info("✓ Spec validation passed")

    # Run Monte Carlo simulation
    logger.info("Running Monte Carlo simulation...")
    spec = ScenarioSpec(**actual_spec)
    monte_carlo_passed, monte_carlo_results = validator.monte_carlo_simulation(spec)

    logger.info(f"Monte Carlo simulation completed")
    logger.debug(f"Results: {monte_carlo_results}")

    if not monte_carlo_passed:
        logger.warning(f"⚠ Monte Carlo simulation failed")
        logger.warning(f"Results: {monte_carlo_results}")
        return ScenarioCompileResponse(
            id=scenario_id,
            status="failed",
            validation_results={
                "valid": True,
                "type": "legacy",
                "monte_carlo_passed": False,
                "monte_carlo_results": monte_carlo_results,
            },
        )

    logger.info("✓ Monte Carlo simulation passed")

    # Update scenario status in database
    db.update_scenario_status(scenario_id, "compiled")
    logger.info(f"✓ Legacy scenario compiled successfully: {scenario_id}")

    return ScenarioCompileResponse(
        id=scenario_id,
        status="compiled",
        validation_results={
            "valid": True,
            "type": "legacy",
            "monte_carlo_passed": True,
            "monte_carlo_results": monte_carlo_results,
        },
    )


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """
    Get a scenario by ID with full specification.

    Args:
        scenario_id: Scenario identifier

    Returns:
        Complete scenario dictionary with spec and metadata

    Raises:
        HTTPException 404: Scenario not found
    """
    logger.debug(f"Retrieving scenario: {scenario_id}")

    scenario = db.get_scenario(scenario_id)
    if not scenario:
        logger.warning(f"Scenario not found: {scenario_id}")
        raise HTTPException(status_code=404, detail="Scenario not found")

    logger.debug(f"Retrieved scenario: {scenario.get('name', 'Unknown')}")
    return scenario


@router.get("/")
async def list_scenarios():
    """
    List all scenarios with summary data.

    Returns:
        Dictionary with 'scenarios' key containing list of scenario summaries
    """
    logger.debug("Listing all scenarios from database...")

    scenarios_list = db.list_scenarios(limit=100)

    logger.debug(f"Returning {len(scenarios_list)} scenarios")
    return {"scenarios": scenarios_list}
