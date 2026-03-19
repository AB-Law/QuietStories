"""
Database manager for QuietStories.

Provides typed CRUD operations for all tables. Each method opens and closes
its own DB session — no session state is held on the manager.
"""

import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import and_, create_engine, desc
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from backend.db.schema import (
    ActorState,
    Base,
    MemoryEntry,
    Scenario,
    Session,
    TurnLog,
    UserSettings,
    WorldState,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """CRUD access for all QuietStories tables."""

    def __init__(self, db_path: str = "data/quietstories.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized at {db_path}")

    @contextmanager
    def _session(self) -> Generator[DBSession, None, None]:
        db: DBSession = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ==================== Scenarios ====================

    def save_scenario(self, scenario_id: str, name: str, spec: Dict[str, Any], status: str = "generated") -> None:
        with self._session() as db:
            existing = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if existing:
                existing.name = name
                existing.spec = spec
                existing.status = status
                existing.updated_at = datetime.utcnow()
            else:
                db.add(Scenario(id=scenario_id, name=name, spec=spec, status=status))

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as db:
            row = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if not row:
                return None
            return {"id": row.id, "name": row.name, "spec": row.spec, "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None}

    def list_scenarios(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._session() as db:
            rows = db.query(Scenario).order_by(desc(Scenario.created_at)).limit(limit).all()
            return [{"id": r.id, "name": r.name, "status": r.status,
                     "created_at": r.created_at.isoformat() if r.created_at else None}
                    for r in rows]

    def update_scenario_status(self, scenario_id: str, status: str) -> bool:
        with self._session() as db:
            row = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if not row:
                return False
            row.status = status
            row.updated_at = datetime.utcnow()
            return True

    # ==================== Sessions ====================

    def create_session(self, scenario_id: str, global_state: Dict[str, Any]) -> str:
        session_id = str(uuid.uuid4())
        with self._session() as db:
            db.add(Session(id=session_id, scenario_id=scenario_id, global_state=global_state))
        logger.info(f"Created session {session_id} for scenario {scenario_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as db:
            row = db.query(Session).filter(Session.id == session_id).first()
            if not row:
                return None
            return {"id": row.id, "scenario_id": row.scenario_id, "turn": row.turn,
                    "global_state": row.global_state, "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None}

    def list_sessions(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._session() as db:
            q = db.query(Session)
            if status:
                q = q.filter(Session.status == status)
            rows = q.order_by(desc(Session.updated_at)).limit(limit).all()
            return [{"id": r.id, "scenario_id": r.scenario_id, "turn": r.turn, "status": r.status,
                     "updated_at": r.updated_at.isoformat() if r.updated_at else None}
                    for r in rows]

    def update_session(self, session_id: str, turn: Optional[int] = None,
                       global_state: Optional[Dict[str, Any]] = None,
                       status: Optional[str] = None) -> bool:
        with self._session() as db:
            row = db.query(Session).filter(Session.id == session_id).first()
            if not row:
                return False
            if turn is not None:
                row.turn = turn
            if global_state is not None:
                row.global_state = global_state
            if status is not None:
                row.status = status
            row.updated_at = datetime.utcnow()
            return True

    # ==================== World State ====================

    def save_world_state(self, session_id: str, locations: Dict[str, Any],
                         factions: Dict[str, Any], time_of_day: str, day: int,
                         active_events: List[Any]) -> None:
        with self._session() as db:
            row = db.query(WorldState).filter(WorldState.session_id == session_id).first()
            if row:
                row.locations = locations
                row.factions = factions
                row.time_of_day = time_of_day
                row.day = day
                row.active_events = active_events
                row.updated_at = datetime.utcnow()
            else:
                db.add(WorldState(
                    session_id=session_id, locations=locations, factions=factions,
                    time_of_day=time_of_day, day=day, active_events=active_events,
                ))

    def get_world_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as db:
            row = db.query(WorldState).filter(WorldState.session_id == session_id).first()
            if not row:
                return None
            return {"locations": row.locations, "factions": row.factions,
                    "time_of_day": row.time_of_day, "day": row.day,
                    "active_events": row.active_events}

    # ==================== Actor State ====================

    def save_actor(self, session_id: str, actor_id: str, data: Dict[str, Any]) -> None:
        """
        Upsert an actor's state for a session.

        data keys: name, personality, background, is_player, location_id,
                   state, goals, relationships, known_facts, last_action_turn
        """
        with self._session() as db:
            row = (db.query(ActorState)
                   .filter(and_(ActorState.session_id == session_id,
                                ActorState.actor_id == actor_id))
                   .first())
            if row:
                for key, value in data.items():
                    if hasattr(row, key):
                        setattr(row, key, value)
                row.updated_at = datetime.utcnow()
            else:
                db.add(ActorState(session_id=session_id, actor_id=actor_id, **data))

    def get_actor(self, session_id: str, actor_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as db:
            row = (db.query(ActorState)
                   .filter(and_(ActorState.session_id == session_id,
                                ActorState.actor_id == actor_id))
                   .first())
            return self._actor_to_dict(row) if row else None

    def get_all_actors(self, session_id: str) -> List[Dict[str, Any]]:
        with self._session() as db:
            rows = db.query(ActorState).filter(ActorState.session_id == session_id).all()
            return [self._actor_to_dict(r) for r in rows]

    def get_actors_at_location(self, session_id: str, location_id: str) -> List[Dict[str, Any]]:
        with self._session() as db:
            rows = (db.query(ActorState)
                    .filter(and_(ActorState.session_id == session_id,
                                 ActorState.location_id == location_id))
                    .all())
            return [self._actor_to_dict(r) for r in rows]

    def get_player_actor(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as db:
            row = (db.query(ActorState)
                   .filter(and_(ActorState.session_id == session_id,
                                ActorState.is_player == True))
                   .first())
            return self._actor_to_dict(row) if row else None

    def _actor_to_dict(self, row: ActorState) -> Dict[str, Any]:
        return {
            "actor_id": row.actor_id,
            "session_id": row.session_id,
            "is_player": row.is_player,
            "name": row.name,
            "personality": row.personality,
            "background": row.background,
            "location_id": row.location_id,
            "state": row.state,
            "goals": row.goals,
            "relationships": row.relationships,
            "known_facts": row.known_facts,
            "last_action_turn": row.last_action_turn,
        }

    # ==================== Memory Entries ====================

    def add_memory(self, session_id: str, actor_id: str, turn: int,
                   content: str, tags: List[str], visibility: str = "private") -> str:
        memory_id = str(uuid.uuid4())
        with self._session() as db:
            db.add(MemoryEntry(
                id=memory_id, session_id=session_id, actor_id=actor_id,
                turn=turn, content=content, tags=tags, visibility=visibility,
            ))
        return memory_id

    def get_recent_memories(self, session_id: str, actor_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the N most recent memories for an actor."""
        with self._session() as db:
            rows = (db.query(MemoryEntry)
                    .filter(and_(MemoryEntry.session_id == session_id,
                                 MemoryEntry.actor_id == actor_id))
                    .order_by(desc(MemoryEntry.turn))
                    .limit(limit)
                    .all())
            return [self._memory_to_dict(r) for r in rows]

    def get_tagged_memories(self, session_id: str, actor_id: str,
                            tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get memories for an actor whose tags overlap with the given tags.

        Used to surface relevant older memories for the current scene:
        pass in the current location ID, IDs of present actors, and topic keywords.
        """
        if not tags:
            return []
        with self._session() as db:
            rows = (db.query(MemoryEntry)
                    .filter(and_(MemoryEntry.session_id == session_id,
                                 MemoryEntry.actor_id == actor_id))
                    .order_by(desc(MemoryEntry.turn))
                    .all())
            # Filter in Python — SQLite JSON array overlap isn't easy without extensions
            matched = []
            tag_set = set(tags)
            for row in rows:
                if tag_set & set(row.tags or []):
                    matched.append(self._memory_to_dict(row))
                    if len(matched) >= limit:
                        break
            return matched

    def get_memories_older_than(self, session_id: str, actor_id: str, turn: int) -> List[Dict[str, Any]]:
        """Get all memories for an actor from before a given turn (for the summarizer)."""
        with self._session() as db:
            rows = (db.query(MemoryEntry)
                    .filter(and_(MemoryEntry.session_id == session_id,
                                 MemoryEntry.actor_id == actor_id,
                                 MemoryEntry.turn < turn))
                    .order_by(MemoryEntry.turn)
                    .all())
            return [self._memory_to_dict(r) for r in rows]

    def get_public_memories(self, session_id: str, since_turn: int = 0) -> List[Dict[str, Any]]:
        """Get all public memories (world events) since a given turn."""
        with self._session() as db:
            rows = (db.query(MemoryEntry)
                    .filter(and_(MemoryEntry.session_id == session_id,
                                 MemoryEntry.visibility == "public",
                                 MemoryEntry.turn >= since_turn))
                    .order_by(MemoryEntry.turn)
                    .all())
            return [self._memory_to_dict(r) for r in rows]

    def _memory_to_dict(self, row: MemoryEntry) -> Dict[str, Any]:
        return {
            "id": row.id,
            "actor_id": row.actor_id,
            "turn": row.turn,
            "content": row.content,
            "tags": row.tags,
            "visibility": row.visibility,
        }

    # ==================== Turn Log ====================

    def append_turn(self, session_id: str, turn: int, player_action: str,
                    narrator_output: Dict[str, Any], npc_decisions: List[Dict[str, Any]],
                    roll_results: List[Dict[str, Any]]) -> None:
        with self._session() as db:
            db.add(TurnLog(
                session_id=session_id, turn=turn, player_action=player_action,
                narrator_output=narrator_output, npc_decisions=npc_decisions,
                roll_results=roll_results,
            ))

    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self._session() as db:
            rows = (db.query(TurnLog)
                    .filter(TurnLog.session_id == session_id)
                    .order_by(desc(TurnLog.turn))
                    .limit(limit)
                    .all())
            return [self._turn_to_dict(r) for r in reversed(rows)]

    def get_turns_older_than(self, session_id: str, turn: int) -> List[Dict[str, Any]]:
        """Used by the summarizer to read older turns before distilling them."""
        with self._session() as db:
            rows = (db.query(TurnLog)
                    .filter(and_(TurnLog.session_id == session_id, TurnLog.turn < turn))
                    .order_by(TurnLog.turn)
                    .all())
            return [self._turn_to_dict(r) for r in rows]

    def _turn_to_dict(self, row: TurnLog) -> Dict[str, Any]:
        return {
            "turn": row.turn,
            "player_action": row.player_action,
            "narrator_output": row.narrator_output,
            "npc_decisions": row.npc_decisions,
            "roll_results": row.roll_results,
        }

    # ==================== User Settings ====================

    def save_user_settings(self, player_name: str, preferences: Dict[str, Any]) -> None:
        with self._session() as db:
            row = db.query(UserSettings).first()
            if row:
                row.player_name = player_name
                row.preferences = preferences
                row.updated_at = datetime.utcnow()
            else:
                db.add(UserSettings(player_name=player_name, preferences=preferences))

    def get_user_settings(self) -> Optional[Dict[str, Any]]:
        with self._session() as db:
            row = db.query(UserSettings).first()
            if not row:
                return None
            return {"id": row.id, "player_name": row.player_name, "preferences": row.preferences}
