"""
Database schema for QuietStories.

Tables:
  scenarios      - ScenarioSpec blueprints (generated, not per-session)
  sessions       - Active game sessions
  world_state    - Per-session world state (locations, factions, time) — pinned Tier 1
  actors         - Per-session actor state (identity, goals, relationships) — pinned Tier 2
  memory_entries - Per-session memory log, retrieved selectively — Tier 3
  turn_log       - Full record of every turn for debugging and history
  user_settings  - User preferences
"""

# mypy: ignore-errors

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Scenario(Base):
    """
    A generated scenario blueprint.
    Stored once and can be used to start multiple sessions.
    """

    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    spec = Column(JSON, nullable=False)  # Full ScenarioSpec as JSON
    status = Column(String, nullable=False, default="generated")  # generated | ready | failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Session(Base):
    """
    An active game session.
    Holds the top-level session state — the per-actor and world data
    live in their own tables, keyed by session_id.
    """

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_id = Column(String, nullable=False)
    turn = Column(Integer, nullable=False, default=0)
    global_state = Column(JSON, nullable=False, default=dict)  # day, weather, custom flags
    status = Column(String, nullable=False, default="active")  # active | completed | failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WorldState(Base):
    """
    Per-session world state — Tier 1 context, always pinned into every prompt.

    Stores locations, factions, time, and active world events.
    Kept compact so it fits comfortably in every LLM context.
    """

    __tablename__ = "world_state"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)
    locations = Column(JSON, nullable=False, default=dict)   # { location_id: { name, description, state } }
    factions = Column(JSON, nullable=False, default=dict)    # { faction_id: { name, description, disposition } }
    time_of_day = Column(String, nullable=False, default="dawn")
    day = Column(Integer, nullable=False, default=1)
    active_events = Column(JSON, nullable=False, default=list)  # [ { id, description, turns_remaining } ]
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ActorState(Base):
    """
    Per-session actor state — Tier 2 context, pinned when an actor is active.

    One row per actor per session. Updated every turn the actor participates in.
    known_facts is the distilled memory summary — always in context, never truncated.
    """

    __tablename__ = "actor_state"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=False, index=True)
    is_player = Column(Boolean, nullable=False, default=False)

    # Identity (set at init, rarely changes)
    name = Column(String, nullable=False)
    personality = Column(Text, nullable=False)
    background = Column(Text, nullable=False)

    # Mutable state
    location_id = Column(String, nullable=False)
    state = Column(JSON, nullable=False, default=dict)          # health, mood, inventory, etc.
    goals = Column(JSON, nullable=False, default=list)          # List[Goal]
    relationships = Column(JSON, nullable=False, default=list)  # List[Relationship]

    # Tier 2 memory: always in context, rewritten by summarizer every N turns
    known_facts = Column(JSON, nullable=False, default=list)    # List[str] bullet points

    # Scheduling: when this actor last took an action (used for off-scene NPC cadence)
    last_action_turn = Column(Integer, nullable=False, default=0)

    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MemoryEntry(Base):
    """
    Per-session memory log — Tier 3 context, retrieved selectively.

    One row per memory. Retrieved by recency and by tag matching against
    the current scene (location, actors present, topics).

    Tags enable cheap retrieval without vector search:
      - Include location IDs, actor IDs present, and topic keywords
      - e.g. ['loc_market', 'elena', 'betrayal', 'guild']
    """

    __tablename__ = "memory_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=False, index=True)   # who this memory belongs to
    turn = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False, default=list)       # List[str]
    visibility = Column(String, nullable=False, default="private")  # private | public
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TurnLog(Base):
    """
    Full record of every turn — for debugging, history display, and summarization.

    Stores the raw inputs and outputs so the summarizer can read older turns
    and distill them into known_facts without relying on LLM context.
    """

    __tablename__ = "turn_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)
    turn = Column(Integer, nullable=False, index=True)
    player_action = Column(Text, nullable=False)
    narrator_output = Column(JSON, nullable=False)    # NarratorOutput as JSON
    npc_decisions = Column(JSON, nullable=False, default=list)  # List[NPCDecision | OffSceneNPCDecision]
    roll_results = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserSettings(Base):
    """User preferences."""

    __tablename__ = "user_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_name = Column(String, nullable=False, default="Player")
    preferences = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
