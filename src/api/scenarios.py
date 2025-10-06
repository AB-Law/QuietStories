"""
Scenario management API endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid
from src.engine.generator import ScenarioGenerator
from src.engine.validator import ScenarioValidator
from src.schemas import ScenarioSpec

router = APIRouter()

# In-memory storage for scenarios (replace with database in production)
scenarios_db: Dict[str, Dict[str, Any]] = {}


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
    
    try:
        generator = ScenarioGenerator()
        scenario_spec = await generator.generate_scenario(request.description)
        
        # Store the scenario
        scenario_id = str(uuid.uuid4())
        scenarios_db[scenario_id] = {
            "id": scenario_id,
            "spec": scenario_spec.dict(),
            "status": "generated"
        }
        
        return ScenarioGenerateResponse(
            id=scenario_id,
            name=scenario_spec.name,
            spec_version=scenario_spec.spec_version,
            status="generated"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate scenario: {e}")


@router.post("/{scenario_id}/compile", response_model=ScenarioCompileResponse)
async def compile_scenario(scenario_id: str, request: ScenarioCompileRequest):
    """Validate and compile a scenario specification"""
    
    if scenario_id not in scenarios_db:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    try:
        validator = ScenarioValidator()
        
        # Validate the spec
        is_valid, issues = validator.validate_spec(request.spec)
        
        if not is_valid:
            # Try auto-repair
            repaired_spec = validator.auto_repair(request.spec, issues)
            is_valid, issues = validator.validate_spec(repaired_spec)
            
            if not is_valid:
                return ScenarioCompileResponse(
                    id=scenario_id,
                    status="failed",
                    validation_results={
                        "valid": False,
                        "issues": issues,
                        "auto_repair_attempted": True
                    }
                )
        
        # Run Monte Carlo simulation
        spec = ScenarioSpec(**request.spec)
        monte_carlo_passed, monte_carlo_results = validator.monte_carlo_simulation(spec)
        
        if not monte_carlo_passed:
            return ScenarioCompileResponse(
                id=scenario_id,
                status="failed",
                validation_results={
                    "valid": True,
                    "monte_carlo_passed": False,
                    "monte_carlo_results": monte_carlo_results
                }
            )
        
        # Update scenario status
        scenarios_db[scenario_id]["status"] = "compiled"
        scenarios_db[scenario_id]["spec"] = request.spec
        
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
        raise HTTPException(status_code=400, detail=f"Failed to compile scenario: {e}")


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get a scenario by ID"""
    
    if scenario_id not in scenarios_db:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenarios_db[scenario_id]


@router.get("/")
async def list_scenarios():
    """List all scenarios"""
    
    return {
        "scenarios": [
            {
                "id": scenario_id,
                "name": scenario["spec"].get("name", "Unknown"),
                "status": scenario["status"]
            }
            for scenario_id, scenario in scenarios_db.items()
        ]
    }
