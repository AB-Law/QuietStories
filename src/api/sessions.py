"""
Session management API endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid
import json
from ..schemas import Outcome

router = APIRouter()

# In-memory storage for sessions (replace with database in production)
sessions_db: Dict[str, Dict[str, Any]] = {}


class SessionCreateRequest(BaseModel):
    """Request to create a new session"""
    scenario_id: str
    seed: int = None


class SessionCreateResponse(BaseModel):
    """Response from session creation"""
    id: str
    scenario_id: str
    status: str


class SessionTurnRequest(BaseModel):
    """Request for a turn in a session"""
    action: str = None
    parameters: Dict[str, Any] = {}


@router.post("/", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new session from a compiled scenario"""
    
    # For now, just create a session without validation
    # In production, you'd validate the scenario exists and is compiled
    
    session_id = str(uuid.uuid4())
    sessions_db[session_id] = {
        "id": session_id,
        "scenario_id": request.scenario_id,
        "seed": request.seed or 12345,
        "state": {},
        "turn": 0,
        "status": "active"
    }
    
    return SessionCreateResponse(
        id=session_id,
        scenario_id=request.scenario_id,
        status="created"
    )


@router.get("/{session_id}/turns")
async def stream_turns(session_id: str):
    """Stream turns for a session (SSE)"""
    
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_db[session_id]
    
    async def generate_turns():
        """Generate turn events for SSE streaming"""
        
        # Send initial turn
        yield f"data: {json.dumps({'type': 'turn_start', 'turn': session['turn']})}\n\n"
        
        # Simulate turn processing
        yield f"data: {json.dumps({'type': 'narrative_chunk', 'content': 'The story begins...'})}\n\n"
        
        # Send turn complete
        yield f"data: {json.dumps({'type': 'turn_complete', 'turn': session['turn']})}\n\n"
        
        # Update session
        session['turn'] += 1
    
    return StreamingResponse(
        generate_turns(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/{session_id}/turns")
async def process_turn(session_id: str, request: SessionTurnRequest):
    """Process a turn in a session"""
    
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_db[session_id]
    
    # For now, return a mock outcome
    # In production, this would use the orchestrator
    outcome = Outcome(
        narrative="You take an action and the story continues...",
        state_changes=[
            {
                "op": "set",
                "path": "state.turn",
                "value": session['turn'] + 1
            }
        ]
    )
    
    # Update session
    session['turn'] += 1
    
    return {
        "session_id": session_id,
        "turn": session['turn'],
        "outcome": outcome.dict()
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get a session by ID"""
    
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions_db[session_id]


@router.get("/")
async def list_sessions():
    """List all sessions"""
    
    return {
        "sessions": [
            {
                "id": session_id,
                "scenario_id": session["scenario_id"],
                "turn": session["turn"],
                "status": session["status"]
            }
            for session_id, session in sessions_db.items()
        ]
    }
