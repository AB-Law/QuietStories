"""
Session API endpoints.

Routes:
  POST /sessions/                      Create a new session from a scenario
  GET  /sessions/                      List all sessions
  GET  /sessions/{id}                  Get full session state
  POST /sessions/{id}/turns            Process a player turn
  GET  /sessions/{id}/actors           Get all actor states for a session
  GET  /sessions/{id}/actors/{actor_id} Get a single actor's state
  GET  /sessions/{id}/memories/{actor_id} Get memories for an actor
  GET  /sessions/{id}/turns            Get recent turn history
  DELETE /sessions/{id}                Delete a session
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.engine.initializer import SessionInitializer
from backend.engine.turn_engine import TurnEngine
from backend.providers import create_provider
from backend.schemas import ScenarioSpec, TurnInput, TurnOutput
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
db = DatabaseManager(settings.database_path)


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    scenario_id: str
    player_name: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    scenario_id: str
    opening_narrative: str
    status: str


class TurnRequest(BaseModel):
    action: str


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _load_spec(scenario_id: str) -> ScenarioSpec:
    scenario = db.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    try:
        return ScenarioSpec(**scenario["spec"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid scenario spec: {e}")


def _get_session_or_404(session_id: str) -> Dict[str, Any]:
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """Initialize a new session from a scenario spec."""
    spec = _load_spec(request.scenario_id)

    # Resolve player name: request → user settings → spec player name
    player_name = request.player_name
    if not player_name:
        user_settings = db.get_user_settings()
        if user_settings:
            player_name = user_settings.get("player_name")

    provider = create_provider()
    initializer = SessionInitializer(db, provider)

    try:
        session_id = await initializer.initialize(spec, scenario_db_id=request.scenario_id, player_name=player_name)
    except Exception as e:
        logger.error(f"Session initialization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Session initialization failed: {e}")

    # Fetch the opening narrative from turn 0
    turns = db.get_recent_turns(session_id, limit=1)
    opening = turns[0]["narrator_output"]["narrative"] if turns else f"Welcome to {spec.name}."

    logger.info(f"Session {session_id} created for scenario {request.scenario_id}")
    return SessionCreateResponse(
        session_id=session_id,
        scenario_id=request.scenario_id,
        opening_narrative=opening,
        status="active",
    )


@router.get("/")
async def list_sessions():
    """List all sessions."""
    return {"sessions": db.list_sessions()}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get full session state including world state and actor list."""
    session = _get_session_or_404(session_id)
    world = db.get_world_state(session_id)
    actors = db.get_all_actors(session_id)
    return {**session, "world": world, "actors": actors}


@router.post("/{session_id}/turns", response_model=TurnOutput)
async def process_turn(session_id: str, request: TurnRequest):
    """Process a player action and return the full turn result."""
    session = _get_session_or_404(session_id)

    if session["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not active (status: {session['status']})",
        )

    spec = _load_spec(session["scenario_id"])
    provider = create_provider()
    engine = TurnEngine(db, provider, spec)

    try:
        result = await engine.process_turn(
            TurnInput(session_id=session_id, action=request.action)
        )
    except Exception as e:
        logger.error(f"Turn processing failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Turn processing failed: {e}")

    return result


@router.get("/{session_id}/actors")
async def get_actors(session_id: str):
    """Get all actor states for a session."""
    _get_session_or_404(session_id)
    return {"actors": db.get_all_actors(session_id)}


@router.get("/{session_id}/actors/{actor_id}")
async def get_actor(session_id: str, actor_id: str):
    """Get a single actor's full state."""
    _get_session_or_404(session_id)
    actor = db.get_actor(session_id, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    return actor


@router.get("/{session_id}/memories")
async def get_session_memories(session_id: str):
    """Get all memories for a session, grouped by actor and visibility."""
    _get_session_or_404(session_id)
    actors = db.get_all_actors(session_id)

    private_memory: Dict[str, list] = {}
    public_memory: Dict[str, list] = {}

    for actor in actors:
        actor_id = actor["actor_id"]
        memories = db.get_recent_memories(session_id, actor_id, limit=50)
        priv = [{"content": m["content"], "turn": m["turn"]} for m in memories if m["visibility"] == "private"]
        pub = [{"content": m["content"], "turn": m["turn"]} for m in memories if m["visibility"] == "public"]
        if priv:
            private_memory[actor_id] = priv
        if pub:
            public_memory[actor_id] = pub

    return {"private_memory": private_memory, "public_memory": public_memory}


@router.get("/{session_id}/relationships")
async def get_session_relationships(session_id: str):
    """Get relationship graph for a session, derived from actor state."""
    _get_session_or_404(session_id)
    actors = db.get_all_actors(session_id)

    relationships: Dict[str, dict] = {}

    for actor in actors:
        actor_a = actor["actor_id"]
        for rel in (actor.get("relationships") or []):
            actor_b = rel.get("actor_id", "")
            if not actor_b:
                continue
            key = f"{min(actor_a, actor_b)}:{max(actor_a, actor_b)}"
            if key not in relationships:
                relationships[key] = {
                    "entity_a": actor_a,
                    "entity_b": actor_b,
                    "sentiment": rel.get("score", 0.0),
                    "relationship_type": rel.get("summary", "")[:80],
                    "memory_count": 0,
                    "last_interaction": rel.get("last_interaction_turn", 0),
                }

    return {
        "session_id": session_id,
        "relationships": relationships,
        "entity_count": len(actors),
        "total_relationships": len(relationships),
    }


@router.get("/{session_id}/memories/{actor_id}")
async def get_actor_memories(session_id: str, actor_id: str, limit: int = 20):
    """Get recent memories for a specific actor."""
    _get_session_or_404(session_id)
    memories = db.get_recent_memories(session_id, actor_id, limit=limit)
    return {"actor_id": actor_id, "memories": memories, "count": len(memories)}


@router.get("/{session_id}/turns")
async def get_turn_history(session_id: str, limit: int = 10):
    """Get recent turn history for a session."""
    _get_session_or_404(session_id)
    turns = db.get_recent_turns(session_id, limit=limit)
    return {"turns": turns, "count": len(turns)}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all associated data."""
    _get_session_or_404(session_id)
    # DatabaseManager handles cascading deletes via SQLAlchemy or we clean up manually
    # For SQLite without FK cascades, we note that memory_entries, actor_state, etc.
    # are scoped by session_id and can be cleaned on demand.
    # For now, mark as deleted — full cleanup can be a background task.
    db.update_session(session_id, status="deleted")
    logger.info(f"Session {session_id} marked as deleted")
    return {"message": f"Session {session_id} deleted"}
