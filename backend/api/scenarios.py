"""
Scenario API endpoints.

Routes:
  POST /scenarios/generate       Generate a new scenario from a description
  POST /scenarios/{id}/validate  Validate a scenario spec
  GET  /scenarios/{id}           Get a scenario by ID
  GET  /scenarios/               List all scenarios
"""

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.engine.generator import ScenarioGenerator
from backend.engine.validator import ScenarioValidator
from backend.schemas import ScenarioSpec, validate_scenario_spec
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
db = DatabaseManager(settings.database_path)


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    description: str


class GenerateResponse(BaseModel):
    id: str
    name: str
    spec_version: str
    status: str


class ValidateResponse(BaseModel):
    id: str
    valid: bool
    issues: list


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/generate", response_model=GenerateResponse)
async def generate_scenario(request: GenerateRequest):
    """Generate a ScenarioSpec from a free-text description."""
    logger.info(f"Generating scenario: {request.description[:80]}...")

    try:
        generator = ScenarioGenerator()
        spec = await generator.generate_scenario(request.description)
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Generation failed: {e}")

    scenario_id = str(uuid.uuid4())
    db.save_scenario(
        scenario_id=scenario_id,
        name=spec.name,
        spec=spec.model_dump(),
        status="generated",
    )

    logger.info(f"Scenario {scenario_id} saved: {spec.name}")
    return GenerateResponse(
        id=scenario_id,
        name=spec.name,
        spec_version=spec.spec_version,
        status="generated",
    )


@router.post("/{scenario_id}/validate", response_model=ValidateResponse)
async def validate_scenario(scenario_id: str):
    """Validate a scenario spec and mark it ready if valid."""
    scenario = db.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    validator = ScenarioValidator()
    is_valid, issues = validator.validate_spec(scenario["spec"])

    if is_valid:
        db.update_scenario_status(scenario_id, "ready")
        logger.info(f"Scenario {scenario_id} validated and marked ready")
    else:
        # Attempt auto-repair
        repaired = validator.auto_repair(scenario["spec"], issues)
        is_valid, issues = validator.validate_spec(repaired)
        if is_valid:
            db.save_scenario(
                scenario_id=scenario_id,
                name=scenario["name"],
                spec=repaired,
                status="ready",
            )
            logger.info(f"Scenario {scenario_id} auto-repaired and marked ready")

    return ValidateResponse(id=scenario_id, valid=is_valid, issues=issues)


@router.get("/")
async def list_scenarios():
    """List all scenarios."""
    return {"scenarios": db.list_scenarios()}


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get a scenario by ID including the full spec."""
    scenario = db.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario
