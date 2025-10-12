"""
Scenario management API endpoints.

This module handles scenario generation, compilation, and validation.
Scenarios are stored in SQLite via DatabaseManager for persistence.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid
from backend.engine.generator import ScenarioGenerator
from backend.engine.validator import ScenarioValidator
from backend.schemas import ScenarioSpec
from backend.db.manager import DatabaseManager
from backend.config import settings
from backend.utils.logger import get_logger

# Set up logging
logger = get_logger(__name__)

router = APIRouter()

# Database manager for persistent storage
db = DatabaseManager(settings.database_path)


class ScenarioGenerateRequest(BaseModel):
    """Request to generate a new scenario"""
    description: str


class ScenarioGenerateResponse(BaseModel):
    """Response from scenario generation"""
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


@router.post("/generate", response_model=ScenarioGenerateResponse)
async def generate_scenario(request: ScenarioGenerateRequest):
    """Generate a new scenario from free-text description"""
    
    logger.info("="*60)
    logger.info(f"SCENARIO GENERATION REQUEST")
    logger.info(f"Description: {request.description[:100]}...")
    logger.debug(f"Full description: {request.description}")
    
    try:
        logger.debug("Initializing ScenarioGenerator...")
        generator = ScenarioGenerator()
        logger.debug(f"Generator created with provider: {generator.provider.__class__.__name__}")
        
        logger.info("Starting scenario generation...")
        scenario_spec = await generator.generate_scenario(request.description)
        
        logger.info(f"✓ Scenario generated successfully: {scenario_spec.name}")
        logger.debug(f"Spec version: {scenario_spec.spec_version}")
        logger.debug(f"Number of actions: {len(scenario_spec.actions) if scenario_spec.actions else 0}")
        logger.debug(f"Number of entities: {len(scenario_spec.entities) if scenario_spec.entities else 0}")
        
        # Store the scenario in database
        scenario_id = str(uuid.uuid4())
        scenario_data = {
            "id": scenario_id,
            "name": scenario_spec.name,
            "spec": scenario_spec.dict(),
            "status": "generated"
        }
        db.save_scenario(scenario_data)
        logger.info(f"Scenario stored with ID: {scenario_id}")
        logger.debug("Scenario saved to database")
        
        return ScenarioGenerateResponse(
            id=scenario_id,
            name=scenario_spec.name,
            spec_version=scenario_spec.spec_version,
            status="generated"
        )
        
    except Exception as e:
        logger.error(f"✗ Scenario generation failed")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to generate scenario: {type(e).__name__}: {str(e)}")


@router.post("/{scenario_id}/compile", response_model=ScenarioCompileResponse)
async def compile_scenario(scenario_id: str):
    """Validate and compile a scenario specification"""
    
    logger.info("="*60)
    logger.info(f"SCENARIO COMPILATION REQUEST")
    logger.info(f"Scenario ID: {scenario_id}")
    
    # Get scenario from database
    scenario = db.get_scenario(scenario_id)
    if not scenario:
        logger.warning(f"✗ Scenario not found: {scenario_id}")
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    try:
        # Get the spec from the scenario
        spec_dict = scenario["spec"]
        scenario_name = spec_dict.get('name', 'Unknown')
        logger.info(f"Retrieved spec for scenario: {scenario_name}")
        logger.debug(f"Spec keys: {list(spec_dict.keys())}")
        
        logger.debug("Initializing ScenarioValidator...")
        validator = ScenarioValidator()
        
        # Validate the spec
        logger.info("Validating scenario specification...")
        is_valid, issues = validator.validate_spec(spec_dict)
        
        if not is_valid:
            logger.warning(f"⚠ Spec validation failed with {len(issues)} issues")
            for i, issue in enumerate(issues[:5], 1):  # Log first 5 issues
                logger.warning(f"  Issue {i}: {issue}")
            if len(issues) > 5:
                logger.warning(f"  ... and {len(issues) - 5} more issues")
            
            # Try auto-repair
            logger.info("Attempting auto-repair...")
            repaired_spec = validator.auto_repair(spec_dict, issues)
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
                        "issues": issues,
                        "auto_repair_attempted": True
                    }
                )
            # Use repaired spec
            spec_dict = repaired_spec
            logger.info("✓ Auto-repair successful")
        else:
            logger.info("✓ Spec validation passed")
        
        # Run Monte Carlo simulation
        logger.info("Running Monte Carlo simulation...")
        logger.debug(f"Simulation parameters: turns={validator.monte_carlo_turns}")
        spec = ScenarioSpec(**spec_dict)
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
                    "monte_carlo_passed": False,
                    "monte_carlo_results": monte_carlo_results
                }
            )
        
        logger.info("✓ Monte Carlo simulation passed")
        
        # Update scenario status in database
        db.update_scenario_status(scenario_id, "compiled")
        logger.info(f"✓ Scenario compiled successfully: {scenario_id}")
        logger.info(f"Scenario '{scenario_name}' is ready for sessions")
        
        return ScenarioCompileResponse(
            id=scenario_id,
            status="compiled",
            validation_results={
                "valid": True,
                "monte_carlo_passed": True,
                "monte_carlo_results": monte_carlo_results
            }
        )
        
    except Exception as e:
        logger.error(f"✗ Compilation failed")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to compile scenario: {type(e).__name__}: {str(e)}")


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
