"""
Session management API endpoints.

This module handles game session creation, turn processing, and persistence.
Sessions are stored in SQLite via DatabaseManager for persistence across restarts.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.engine.initializer import SessionInitializer
from backend.engine.orchestrator import TurnOrchestrator
from backend.schemas import Outcome, ScenarioSpec
from backend.utils.cache import (
    get_cache_statistics,
    invalidate_session_cache,
    memory_cache,
)
from backend.utils.logger import get_logger

# Set up logging
logger = get_logger(__name__)

router = APIRouter()

# Database manager for persistent storage
db = DatabaseManager(settings.database_path)

# In-memory storage for orchestrators (these don't need persistence)
orchestrators_db: Dict[str, TurnOrchestrator] = {}


class SessionConfig(BaseModel):
    """Advanced configuration for session creation"""

    num_characters: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of characters to generate backgrounds for",
    )
    generate_world_background: bool = Field(
        default=True, description="Whether to generate world background"
    )
    generate_entity_backgrounds: bool = Field(
        default=True, description="Whether to generate entity backgrounds"
    )
    initial_entities: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Custom initial entities"
    )
    custom_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom initial state overrides"
    )
    player_name: Optional[str] = Field(
        default=None, description="Player's preferred character name"
    )


class SessionCreateRequest(BaseModel):
    """Request to create a new session"""

    scenario_id: str
    seed: Optional[int] = None
    config: Optional[SessionConfig] = None


class SessionCreateResponse(BaseModel):
    """Response from session creation"""

    id: str
    scenario_id: str
    status: str


class SessionTurnRequest(BaseModel):
    """Request for a turn in a session"""

    action: Optional[str] = None
    parameters: Dict[str, Any] = {}


@router.post("/", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """
    Create a new session from a compiled scenario.

    This endpoint:
    1. Validates the scenario exists and is compiled
    2. Generates world background and entity details
    3. Creates session in database
    4. Initializes orchestrator

    Args:
        request: Session creation request with scenario_id and optional seed

    Returns:
        SessionCreateResponse with session ID and status

    Raises:
        HTTPException 404: Scenario not found
        HTTPException 400: Scenario not compiled
    """
    logger.info("=" * 60)
    logger.info(f"SESSION CREATION REQUEST")
    logger.info(f"Scenario ID: {request.scenario_id}")
    logger.debug(f"Seed: {request.seed}")

    # Get scenario from database
    scenario_data = db.get_scenario(request.scenario_id)
    if not scenario_data:
        logger.error(f"✗ Scenario not found: {request.scenario_id}")
        raise HTTPException(status_code=404, detail="Scenario not found")

    if scenario_data["status"] != "compiled":
        logger.error(f"✗ Scenario not compiled: {scenario_data['status']}")
        logger.error("Scenario must be compiled before creating a session")
        raise HTTPException(status_code=400, detail="Scenario must be compiled first")

    # Create the scenario spec
    spec_dict = scenario_data["spec"]
    spec = ScenarioSpec(**spec_dict)
    logger.info(f"Loaded scenario spec: {spec.name}")
    logger.debug(f"Spec has {len(spec.actions) if spec.actions else 0} actions")
    logger.debug(f"Spec has {len(spec.entities) if spec.entities else 0} entities")

    # Create session ID
    session_id = str(uuid.uuid4())
    seed_value = request.seed or spec.seed
    initial_state = spec.state.copy() if spec.state else {}

    logger.debug(f"Using seed: {seed_value}")
    logger.debug(f"Initial state keys: {list(initial_state.keys())}")

    # Get config or use defaults
    config = request.config if request.config else SessionConfig()

    # Retrieve user settings for player name if not provided in config
    if not config.player_name:
        user_settings = db.get_user_settings()
        if user_settings:
            config.player_name = user_settings.get("player_name")
            logger.debug(f"Using player name from settings: {config.player_name}")

    logger.debug(
        f"Session config: num_characters={config.num_characters}, gen_world={config.generate_world_background}, gen_entities={config.generate_entity_backgrounds}, player_name={config.player_name}"
    )

    # Apply custom state if provided
    if config.custom_state:
        initial_state.update(config.custom_state)
        logger.debug("Applied custom state overrides")

    # Use custom entities if provided
    if config.initial_entities:
        spec.entities = config.initial_entities
        logger.debug(f"Using {len(config.initial_entities)} custom initial entities")

    # Initialize world and entities based on config
    logger.info("Initializing session world and entities...")
    try:
        initializer = SessionInitializer()
        init_data = await initializer.initialize_session(
            spec,
            session_id,
            num_characters=config.num_characters,
            generate_world=config.generate_world_background,
            generate_entities=config.generate_entity_backgrounds,
            player_name=config.player_name,
        )

        world_background = init_data["world_background"]
        detailed_entities = init_data["entities"]

        logger.info(f"✓ World initialized ({len(world_background)} chars)")
        logger.info(f"✓ {len(detailed_entities)} entities initialized")
    except Exception as e:
        logger.error(f"Session initialization failed: {e}", exc_info=True)
        # Continue with basic data
        world_background = f"Welcome to {spec.name}. Your adventure begins here."
        detailed_entities = spec.entities

    # Create session data
    session_data = {
        "id": session_id,
        "scenario_id": request.scenario_id,
        "seed": seed_value,
        "state": initial_state,
        "turn": 0,
        "turn_history": [],
        "world_background": world_background,
        "entities": detailed_entities,
        "private_memory": {},
        "public_memory": {},
        "status": "active",
        "scenario_spec": spec_dict,
    }

    # Save to database
    logger.debug("Saving session to database...")
    db.save_session(session_data)

    # Create orchestrator for this session
    logger.debug("Creating TurnOrchestrator...")
    orchestrator = TurnOrchestrator(spec, session_id, db)
    orchestrator.set_session_ref(
        session_data
    )  # Set reference for accessing turn history
    orchestrators_db[session_id] = orchestrator

    logger.info(f"✓ Session created successfully: {session_id}")
    logger.debug(f"Total orchestrators: {len(orchestrators_db)}")

    return SessionCreateResponse(
        id=session_id, scenario_id=request.scenario_id, status="created"
    )


@router.get("/{session_id}/turns")
async def stream_turns(session_id: str):
    """Stream turns for a session (SSE)"""

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def generate_turns():
        """Generate turn events for SSE streaming"""

        # Send initial turn
        yield f"data: {json.dumps({'type': 'turn_start', 'turn': session['turn']})}\n\n"

        # Simulate turn processing
        yield f"data: {json.dumps({'type': 'narrative_chunk', 'content': 'The story begins...'})}\n\n"

        # Send turn complete
        yield f"data: {json.dumps({'type': 'turn_complete', 'turn': session['turn']})}\n\n"

        # Update session
        session["turn"] += 1

    return StreamingResponse(
        generate_turns(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{session_id}/turns")
async def process_turn(session_id: str, request: SessionTurnRequest):
    """
    Process a turn in a session.

    This endpoint:
    1. Loads session from database
    2. Processes the turn via orchestrator
    3. Stores turn record in history
    4. Updates session in database

    Args:
        session_id: Session identifier
        request: Turn request with optional action

    Returns:
        Dictionary with session_id, turn number, and outcome

    Raises:
        HTTPException 404: Session not found
    """
    logger.info("=" * 60)
    logger.info(f"TURN PROCESSING REQUEST")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Action: {request.action or '(none - auto turn)'}")
    logger.debug(f"Parameters: {request.parameters}")

    # Load session from database
    session = db.get_session(session_id)
    if not session:
        logger.error(f"✗ Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    current_turn = session["turn"]
    logger.info(f"Current turn: {current_turn}")

    try:
        # Get or create orchestrator
        if session_id not in orchestrators_db:
            logger.warning(
                "Orchestrator not found in cache, recreating from session data..."
            )
            spec = ScenarioSpec(**session["scenario_spec"])
            # Update spec entities with the detailed entities from session
            spec.entities = session.get("entities", spec.entities)
            orchestrator = TurnOrchestrator(spec, session_id, db)
            orchestrator.set_session_ref(
                session
            )  # Set reference for turn history access
            orchestrators_db[session_id] = orchestrator
            logger.info("✓ Orchestrator recreated")
        else:
            orchestrator = orchestrators_db[session_id]
            # Update session reference in case it was reloaded
            orchestrator.set_session_ref(session)

        logger.debug(f"Orchestrator spec: {orchestrator.spec.name}")

        # Log state before turn
        state_before = session.get("state", {})
        logger.debug(f"State before turn (keys): {list(state_before.keys())}")
        logger.debug(
            f"State before turn (preview): {json.dumps(state_before, default=str)[:300]}"
        )

        # Process turn with orchestrator
        logger.info("Calling orchestrator.process_turn...")
        outcome = await orchestrator.process_turn(request.action)

        logger.info(f"✓ Turn processed successfully")
        logger.info(f"Narrative length: {len(outcome.narrative)} characters")
        logger.debug(f"Narrative preview: {outcome.narrative[:200]}...")
        logger.info(f"State changes: {len(outcome.state_changes)} changes")

        for i, change in enumerate(outcome.state_changes[:5], 1):
            logger.debug(f"  Change {i}: {change.op} {change.path} = {change.value}")
        if len(outcome.state_changes) > 5:
            logger.debug(f"  ... and {len(outcome.state_changes) - 5} more changes")

        # Create turn record
        turn_record = {
            "turn": current_turn + 1,
            "timestamp": datetime.now().isoformat(),
            "user_action": request.action,
            "narrative": outcome.narrative,
            "state_changes": (
                [sc.dict() for sc in outcome.state_changes]
                if outcome.state_changes
                else []
            ),
            "visible_dialogue": (
                [vd.dict() for vd in outcome.visible_dialogue]
                if outcome.visible_dialogue
                else []
            ),
            "roll_requests": (
                [rr.dict() for rr in outcome.roll_requests]
                if outcome.roll_requests
                else []
            ),
        }

        # Update session
        new_turn = current_turn + 1
        state_after = orchestrator.spec.state

        # Add turn to history
        turn_history = session.get("turn_history", [])
        turn_history.append(turn_record)

        # Get entities from orchestrator - ALWAYS update to ensure backgrounds persist
        entities = orchestrator.spec.entities
        logger.debug(f"Entities after turn: {len(entities)} entities")
        for entity in entities[:3]:  # Log first 3
            logger.debug(
                f"  - {entity.get('id')}: has background={bool(entity.get('background'))}"
            )

        # Get memories from orchestrator
        private_memory = dict(orchestrator.memory.private_memory)
        public_memory = dict(orchestrator.memory.public_memory)

        # Update in database - ALWAYS include entities to preserve backgrounds
        db.update_session(
            session_id,
            {
                "turn": new_turn,
                "state": state_after,
                "turn_history": turn_history,
                "entities": entities,  # Always save entities to keep backgrounds
                "private_memory": private_memory,
                "public_memory": public_memory,
            },
        )

        # Update session reference for orchestrator
        session["turn"] = new_turn
        session["state"] = state_after
        session["turn_history"] = turn_history
        session["entities"] = entities
        orchestrator.set_session_ref(session)

        logger.debug(f"State after turn (keys): {list(state_after.keys())}")
        logger.info(f"Turn completed. New turn count: {new_turn}")
        logger.info(f"Turn history now has {len(turn_history)} entries")

        # Invalidate caches since session data has changed
        invalidate_session_cache(session_id)

        return {"session_id": session_id, "turn": new_turn, "outcome": outcome.dict()}

    except Exception as e:
        logger.error(f"✗ Turn processing failed")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)

        # Fallback to minimal response
        logger.warning("Creating fallback response...")
        from backend.schemas.outcome import StateChange

        outcome = Outcome(
            narrative=f"Something unexpected happened. Error: {str(e)}",
            state_changes=[
                StateChange(op="set", path="state.turn", value=session["turn"] + 1)
            ],
            visible_dialogue=None,
            roll_requests=None,
            hidden_memory_updates=None,
            emotional_state_updates=None,
            suggested_actions=None,
        )

        session["turn"] += 1

        return {
            "session_id": session_id,
            "turn": session["turn"],
            "outcome": outcome.dict(),
        }


@router.post("/{session_id}/turns/stream")
async def stream_turn_response(session_id: str, request: SessionTurnRequest):
    """
    Stream turn response using Server-Sent Events for real-time narrative generation.

    This endpoint:
    1. Loads session from database
    2. Processes the turn via orchestrator
    3. Streams narrative text as it's generated token-by-token
    4. Sends completion status

    Args:
        session_id: Session identifier
        request: Turn request with optional action

    Yields:
        SSE messages with types: start, narrative_chunk, complete, error
    """
    logger.info("=" * 60)
    logger.info(f"STREAMING TURN REQUEST")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Action: {request.action or '(none - auto turn)'}")

    # Load session from database
    session = db.get_session(session_id)

    async def generate_stream():
        if not session:
            logger.error(f"✗ Session not found: {session_id}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
            return

        current_turn = session["turn"]
        logger.info(f"Current turn: {current_turn}")

        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'start', 'turn': current_turn})}\n\n"

            # Get or create orchestrator
            if session_id not in orchestrators_db:
                logger.warning(
                    "Orchestrator not found in cache, recreating from session data..."
                )
                spec = ScenarioSpec(**session["scenario_spec"])
                spec.entities = session.get("entities", spec.entities)
                orchestrator = TurnOrchestrator(spec, session_id, db)
                orchestrator.set_session_ref(session)
                orchestrators_db[session_id] = orchestrator
                logger.info("✓ Orchestrator recreated")
            else:
                orchestrator = orchestrators_db[session_id]
                orchestrator.set_session_ref(session)

            # Process turn with streaming
            logger.info("Processing turn with streaming...")
            outcome = await orchestrator.process_turn(request.action)

            logger.info(f"✓ Turn processed successfully")
            logger.info(f"Narrative length: {len(outcome.narrative)} characters")

            # Stream the narrative in chunks for smooth UX
            narrative = outcome.narrative
            chunk_size = 100  # characters per chunk for smooth streaming

            if narrative:
                for i in range(0, len(narrative), chunk_size):
                    chunk = narrative[i : i + chunk_size]
                    yield f"data: {json.dumps({'type': 'narrative_chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.05)  # Small delay for smooth streaming effect

            # Apply state changes and update memory (existing logic)
            if outcome.state_changes:
                logger.info(f"Applying {len(outcome.state_changes)} state changes...")
                orchestrator._apply_state_changes(outcome.state_changes)

            # Increment turn counter
            orchestrator.memory.increment_turn()
            logger.info(f"Turn completed: {orchestrator.memory.get_turn_count()}")

            # Save memory to database
            orchestrator.memory.save_to_database()

            # Create turn record for history
            turn_record = {
                "turn": current_turn + 1,
                "timestamp": datetime.now().isoformat(),
                "user_action": request.action,
                "narrative": outcome.narrative,
                "state_changes": (
                    [sc.dict() for sc in outcome.state_changes]
                    if outcome.state_changes
                    else []
                ),
                "visible_dialogue": (
                    [vd.dict() for vd in outcome.visible_dialogue]
                    if outcome.visible_dialogue
                    else []
                ),
                "roll_requests": (
                    [rr.dict() for rr in outcome.roll_requests]
                    if outcome.roll_requests
                    else []
                ),
            }

            # Update session in database
            new_turn = current_turn + 1
            state_after = orchestrator.spec.state

            # Add turn to history
            turn_history = session.get("turn_history", [])
            turn_history.append(turn_record)

            # Get updated entities and memories
            entities = orchestrator.spec.entities
            private_memory = dict(orchestrator.memory.private_memory)
            public_memory = dict(orchestrator.memory.public_memory)

            # Update in database
            db.update_session(
                session_id,
                {
                    "turn": new_turn,
                    "state": state_after,
                    "turn_history": turn_history,
                    "entities": entities,
                    "private_memory": private_memory,
                    "public_memory": public_memory,
                },
            )

            # Update session reference for orchestrator
            session["turn"] = new_turn
            session["state"] = state_after
            session["turn_history"] = turn_history
            session["entities"] = entities
            orchestrator.set_session_ref(session)

            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'turn': new_turn})}\n\n"

        except Exception as e:
            logger.error(f"✗ Streaming turn processing failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{session_id}")
async def get_session(session_id: str):
    """
    Get a session by ID with full data.

    Returns complete session including:
    - Current state and turn number
    - Turn history
    - World background
    - Entities with backgrounds
    - Scenario spec

    Args:
        session_id: Session identifier

    Returns:
        Complete session dictionary

    Raises:
        HTTPException 404: Session not found
    """
    logger.debug(f"Retrieving session: {session_id}")

    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    logger.debug(f"Retrieved session on turn {session['turn']}")
    return session


@router.get("/{session_id}/relationships")
async def get_relationships(session_id: str):
    """
    Get relationship data for all entities in a session.

    Returns relationship analysis including:
    - Sentiment scores between entities
    - Relationship types
    - Interaction frequency

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with relationship data

    Raises:
        HTTPException 404: Session not found
    """
    logger.debug(f"Retrieving relationships for session: {session_id}")

    # Check cache first
    cached_data = memory_cache.get_relationships(session_id)
    if cached_data:
        logger.debug(f"Returning cached relationships for session: {session_id}")
        return cached_data

    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    # Get orchestrator to access memory system
    if session_id not in orchestrators_db:
        # Create temporary orchestrator just to access memory
        import json

        from backend.engine.orchestrator import TurnOrchestrator
        from backend.schemas import ScenarioSpec

        spec = ScenarioSpec(**session["scenario_spec"])
        temp_orchestrator = TurnOrchestrator(spec, session_id, db)
        orchestrators_db[session_id] = temp_orchestrator

    orchestrator = orchestrators_db[session_id]

    # Get relationship summary from memory system
    relationship_summary = orchestrator.memory.get_relationship_summary()

    # Convert tuple keys back to readable format
    formatted_relationships = {}
    for key_tuple, rel_data in relationship_summary.items():
        key = f"{rel_data['entity_a']}_{rel_data['entity_b']}"
        formatted_relationships[key] = {
            "entity_a": rel_data["entity_a"],
            "entity_b": rel_data["entity_b"],
            "sentiment": rel_data["sentiment"],
            "relationship_type": rel_data["relationship_type"],
            "memory_count": rel_data["memory_count"],
            "last_interaction": rel_data["last_interaction"],
        }

    result = {
        "session_id": session_id,
        "relationships": formatted_relationships,
        "entity_count": len(session.get("entities", [])),
        "total_relationships": len(formatted_relationships),
    }

    # Cache the result
    memory_cache.set_relationships(session_id, result)

    return result


@router.get("/")
async def list_sessions():
    """
    List all sessions with summary data.

    Returns:
        Dictionary with 'sessions' key containing list of session summaries
    """
    logger.debug("Listing all sessions from database...")

    sessions_list = db.list_sessions(limit=100)

    logger.debug(f"Returning {len(sessions_list)} sessions")
    return {"sessions": sessions_list}


@router.get("/{session_id}/memories")
async def get_session_memories(session_id: str):
    """
    Get memory data for a session.

    Returns private and public memories for all entities in the session.

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with private_memory and public_memory

    Raises:
        HTTPException 404: Session not found
    """
    logger.debug(f"Fetching memories for session: {session_id}")

    # Check session exists
    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    # Get or create orchestrator
    if session_id not in orchestrators_db:
        logger.debug("Recreating orchestrator to access memories...")
        spec = ScenarioSpec(**session["scenario_spec"])
        orchestrator = TurnOrchestrator(spec, session_id, db)
        orchestrator.set_session_ref(session)
        orchestrators_db[session_id] = orchestrator
    else:
        orchestrator = orchestrators_db[session_id]

    # Get memory data from orchestrator's memory manager
    private_memory = dict(orchestrator.memory.private_memory)
    public_memory = dict(orchestrator.memory.public_memory)

    logger.debug(
        f"Retrieved memories: {len(private_memory)} private, {len(public_memory)} public"
    )
    logger.debug(f"Private memory keys: {list(private_memory.keys())}")
    logger.debug(f"Public memory keys: {list(public_memory.keys())}")

    return {"private_memory": private_memory, "public_memory": public_memory}


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache performance statistics.

    Returns cache hit rates, sizes, and other performance metrics
    for monitoring and optimization.

    Returns:
        Dictionary with cache statistics
    """
    logger.debug("Retrieving cache statistics")

    stats = get_cache_statistics()

    return {"cache_stats": stats, "timestamp": datetime.now().isoformat()}


@router.get("/{session_id}/relationships/{entity_id}")
async def get_entity_relationships(session_id: str, entity_id: str):
    """
    Get relationship summary for a specific entity in a session.

    Returns detailed relationship information including:
    - Outgoing and incoming relationships
    - Relationship types and sentiment scores
    - Strongest relationships

    Args:
        session_id: Session identifier
        entity_id: Entity identifier to get relationships for

    Returns:
        Dictionary with entity relationship summary

    Raises:
        HTTPException 404: Session or entity not found
    """
    logger.debug(
        f"Retrieving relationships for entity {entity_id} in session {session_id}"
    )

    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    # Get orchestrator to access memory system
    if session_id not in orchestrators_db:
        from backend.engine.orchestrator import TurnOrchestrator
        from backend.schemas import ScenarioSpec

        spec = ScenarioSpec(**session["scenario_spec"])
        temp_orchestrator = TurnOrchestrator(spec, session_id, db)
        orchestrators_db[session_id] = temp_orchestrator

    orchestrator = orchestrators_db[session_id]

    # Get relationship summary from memory system
    try:
        relationship_summary = orchestrator.memory.get_entity_relationship_summary(
            entity_id
        )

        return {
            "session_id": session_id,
            "entity_id": entity_id,
            "relationship_summary": relationship_summary,
        }
    except Exception as e:
        logger.error(f"Failed to get relationship summary for {entity_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_id} not found or has no relationships",
        )


@router.get("/{session_id}/graph/summary")
async def get_graph_summary(session_id: str):
    """
    Get overall relationship graph statistics for a session.

    Returns graph-wide statistics including:
    - Total entities and relationships
    - Relationship types distribution
    - Most connected entities

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with graph summary statistics

    Raises:
        HTTPException 404: Session not found
    """
    logger.debug(f"Retrieving graph summary for session {session_id}")

    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    # Get orchestrator to access memory system
    if session_id not in orchestrators_db:
        from backend.engine.orchestrator import TurnOrchestrator
        from backend.schemas import ScenarioSpec

        spec = ScenarioSpec(**session["scenario_spec"])
        temp_orchestrator = TurnOrchestrator(spec, session_id, db)
        orchestrators_db[session_id] = temp_orchestrator

    orchestrator = orchestrators_db[session_id]

    # Get graph summary from memory system
    try:
        graph_summary = orchestrator.memory.get_graph_summary()

        return {
            "session_id": session_id,
            "graph_summary": graph_summary,
        }
    except Exception as e:
        logger.error(f"Failed to get graph summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve graph summary")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and clean up associated resources.

    This endpoint:
    1. Removes session from database
    2. Deletes session-specific ChromaDB collection
    3. Removes orchestrator from memory
    4. Clears any cached data

    Args:
        session_id: Session identifier to delete

    Returns:
        Confirmation message

    Raises:
        HTTPException 404: Session not found
    """
    logger.info(f"Deleting session: {session_id}")

    # Check if session exists
    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found for deletion: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Delete from database
        db.delete_session(session_id)
        logger.info(f"Deleted session {session_id} from database")

        # Delete ChromaDB collection if semantic search is available
        try:
            from backend.engine.memory_search import SemanticMemorySearch

            # Create temporary semantic search instance to access collection
            temp_search = SemanticMemorySearch(session_id)
            if temp_search.is_available() and temp_search.vectorstore:
                # Delete the session-specific collection
                temp_search.vectorstore.delete_collection()
                logger.info(f"Deleted ChromaDB collection for session {session_id}")
        except Exception as e:
            logger.warning(
                f"Failed to delete ChromaDB collection for session {session_id}: {e}"
            )

        # Remove from orchestrator cache
        if session_id in orchestrators_db:
            del orchestrators_db[session_id]
            logger.debug(f"Removed orchestrator for session {session_id}")

        # Clear cache
        memory_cache.clear_session(session_id)
        logger.debug(f"Cleared cache for session {session_id}")

        return {
            "message": f"Session {session_id} deleted successfully",
            "deleted_resources": [
                "database",
                "vector_collection",
                "orchestrator",
                "cache",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/{session_id}/performance")
async def get_session_performance(session_id: str):
    """
    Get performance metrics for a session.

    Returns metrics including:
    - Turn count and duration
    - Tool call statistics
    - Memory usage
    - Response times

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with performance metrics

    Raises:
        HTTPException 404: Session not found
    """
    logger.debug(f"Retrieving performance metrics for session {session_id}")

    session = db.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    # Get orchestrator to access memory statistics
    if session_id not in orchestrators_db:
        from backend.engine.orchestrator import TurnOrchestrator
        from backend.schemas import ScenarioSpec

        spec = ScenarioSpec(**session["scenario_spec"])
        temp_orchestrator = TurnOrchestrator(spec, session_id, db)
        orchestrators_db[session_id] = temp_orchestrator

    orchestrator = orchestrators_db[session_id]

    # Collect performance metrics
    memory_stats = orchestrator.memory.get_memory_statistics()

    # Get semantic search stats if available
    semantic_stats = {}
    if (
        hasattr(orchestrator.memory, "semantic_search")
        and orchestrator.memory.semantic_search.is_available()
    ):
        semantic_stats = orchestrator.memory.semantic_search.get_stats()

    return {
        "session_id": session_id,
        "turn_count": session.get("turn", 0),
        "created_at": session.get("created_at"),
        "memory_stats": memory_stats,
        "semantic_search_stats": semantic_stats,
        "relationship_graph_stats": orchestrator.memory.get_graph_summary(),
    }
