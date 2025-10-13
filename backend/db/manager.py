"""
Database manager for QuietStories.

This module provides a high-level interface for database operations,
handling scenarios and sessions with automatic connection management.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from backend.db.schema import Base, Scenario, Session, UserSettings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages database operations for scenarios and sessions.

    This class provides CRUD operations for scenarios and sessions,
    with automatic schema creation and connection pooling.

    Attributes:
        db_path: Path to the SQLite database file
        engine: SQLAlchemy engine for database connections
        SessionLocal: Factory for creating database sessions
    """

    def __init__(self, db_path: str = "data/quietstories.db"):
        """
        Initialize the database manager.

        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
        """
        self.db_path = db_path

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create engine and tables
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False},  # Allow multi-threading
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Database initialized at {db_path}")

    # ==================== Scenario Operations ====================

    def save_scenario(self, scenario_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a scenario to the database.

        Args:
            scenario_dict: Dictionary containing scenario data with keys:
                - id: Scenario ID
                - name: Scenario name
                - spec: Complete scenario specification
                - status: Scenario status (generated, compiled, etc.)

        Returns:
            Dictionary with saved scenario data

        Raises:
            ValueError: If required fields are missing
        """
        db: DBSession = self.SessionLocal()
        try:
            # Check if scenario exists
            existing = (
                db.query(Scenario).filter(Scenario.id == scenario_dict["id"]).first()
            )

            if existing:
                # Update existing
                existing.name = scenario_dict.get("name", "Unnamed Scenario")
                existing.spec = scenario_dict["spec"]
                existing.status = scenario_dict.get("status", "generated")
                existing.updated_at = datetime.utcnow()  # type: ignore
                scenario = existing
            else:
                # Create new
                scenario = Scenario(
                    id=scenario_dict["id"],
                    name=scenario_dict.get("name", "Unnamed Scenario"),
                    spec=scenario_dict["spec"],
                    status=scenario_dict.get("status", "generated"),
                    created_at=datetime.utcnow(),
                )
                db.add(scenario)

            db.commit()

            # Convert to dict before closing session (don't refresh to avoid lazy loading issues)
            result = {
                "id": scenario.id,
                "name": scenario.name,
                "spec": scenario.spec,
                "status": scenario.status,
                "created_at": (
                    scenario.created_at.isoformat() if scenario.created_at else None
                ),
            }

            logger.debug(f"Saved scenario {result['id']}: {result['name']}")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save scenario: {e}")
            raise
        finally:
            db.close()

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a scenario by ID.

        Args:
            scenario_id: The scenario's unique identifier

        Returns:
            Dictionary containing scenario data, or None if not found
        """
        db: DBSession = self.SessionLocal()
        try:
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if scenario:
                return {
                    "id": scenario.id,
                    "name": scenario.name,
                    "spec": scenario.spec,
                    "status": scenario.status,
                    "created_at": (
                        scenario.created_at.isoformat() if scenario.created_at else None
                    ),
                }
            return None
        finally:
            db.close()

    def list_scenarios(
        self, limit: int = 50, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List scenarios with optional filtering.

        Args:
            limit: Maximum number of scenarios to return
            status: Optional status filter (generated, compiled, etc.)

        Returns:
            List of scenario dictionaries, most recent first
        """
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(Scenario)
            if status:
                query = query.filter(Scenario.status == status)

            scenarios = query.order_by(desc(Scenario.created_at)).limit(limit).all()

            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in scenarios
            ]
        finally:
            db.close()

    def update_scenario_status(self, scenario_id: str, status: str) -> bool:
        """
        Update a scenario's status.

        Args:
            scenario_id: The scenario's unique identifier
            status: New status (generated, compiled, failed)

        Returns:
            True if updated successfully, False if not found
        """
        db: DBSession = self.SessionLocal()
        try:
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if scenario:
                scenario.status = status  # type: ignore
                scenario.updated_at = datetime.utcnow()  # type: ignore
                db.commit()
                logger.debug(f"Updated scenario {scenario_id} status to {status}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update scenario status: {e}")
            raise
        finally:
            db.close()

    # ==================== Session Operations ====================

    def save_session(self, session_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a session to the database.

        Args:
            session_dict: Dictionary containing session data with keys:
                - id: Session ID
                - scenario_id: Related scenario ID
                - state: Current game state
                - turn: Current turn number
                - turn_history: List of turn records
                - world_background: World narrative (optional)
                - entities: List of entities (optional)
                - private_memory: Private entity memories (optional)
                - public_memory: Public entity memories (optional)
                - status: Session status (optional)
                - scenario_spec: Cached scenario spec (optional)

        Returns:
            Dictionary with saved session data

        Raises:
            ValueError: If required fields are missing
        """
        db: DBSession = self.SessionLocal()
        try:
            # Check if session exists
            existing = (
                db.query(Session).filter(Session.id == session_dict["id"]).first()
            )

            if existing:
                # Update existing
                existing.scenario_id = session_dict["scenario_id"]
                existing.seed = session_dict.get("seed")  # type: ignore
                existing.state = session_dict.get("state", {})
                existing.turn = session_dict.get("turn", 0)
                existing.turn_history = session_dict.get("turn_history", [])
                existing.world_background = session_dict.get("world_background")  # type: ignore
                existing.entities = session_dict.get("entities", [])
                existing.private_memory = session_dict.get("private_memory", {})  # type: ignore
                existing.public_memory = session_dict.get("public_memory", {})  # type: ignore
                existing.status = session_dict.get("status", "active")  # type: ignore
                existing.scenario_spec = session_dict.get("scenario_spec")  # type: ignore
                existing.updated_at = datetime.utcnow()  # type: ignore
                session = existing
            else:
                # Create new
                session = Session(
                    id=session_dict["id"],
                    scenario_id=session_dict["scenario_id"],
                    seed=session_dict.get("seed"),
                    state=session_dict.get("state", {}),
                    turn=session_dict.get("turn", 0),
                    turn_history=session_dict.get("turn_history", []),
                    world_background=session_dict.get("world_background"),
                    entities=session_dict.get("entities", []),
                    private_memory=session_dict.get("private_memory", {}),
                    public_memory=session_dict.get("public_memory", {}),
                    status=session_dict.get("status", "active"),
                    scenario_spec=session_dict.get("scenario_spec"),
                    created_at=datetime.utcnow(),
                )
                db.add(session)

            db.commit()

            result = {  # type: ignore
                "id": session.id,  # type: ignore
                "scenario_id": session.scenario_id,  # type: ignore
                "seed": session.seed,  # type: ignore
                "state": session.state,  # type: ignore
                "turn": session.turn,  # type: ignore
                "turn_history": session.turn_history or [],  # type: ignore
                "world_background": session.world_background,  # type: ignore
                "entities": session.entities or [],  # type: ignore
                "private_memory": session.private_memory or {},  # type: ignore
                "public_memory": session.public_memory or {},  # type: ignore
                "status": session.status,  # type: ignore
                "scenario_spec": session.scenario_spec,  # type: ignore
                "created_at": (
                    session.created_at.isoformat() if session.created_at else None
                ),
            }

            logger.debug(f"Saved session {result['id']} at turn {result['turn']}")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save session: {e}")
            raise
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.

        Args:
            session_id: The session's unique identifier

        Returns:
            Dictionary containing complete session data, or None if not found
        """
        db: DBSession = self.SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                return {
                    "id": session.id,
                    "scenario_id": session.scenario_id,
                    "seed": session.seed,
                    "state": session.state,
                    "turn": session.turn,
                    "turn_history": session.turn_history or [],
                    "world_background": session.world_background,
                    "entities": session.entities or [],
                    "private_memory": session.private_memory or {},
                    "public_memory": session.public_memory or {},
                    "status": session.status,
                    "scenario_spec": session.scenario_spec,
                    "created_at": (
                        session.created_at.isoformat() if session.created_at else None
                    ),
                    "updated_at": (
                        session.updated_at.isoformat() if session.updated_at else None
                    ),
                }
            return None
        finally:
            db.close()

    def list_sessions(
        self, limit: int = 50, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filtering.

        Args:
            limit: Maximum number of sessions to return
            status: Optional status filter (active, completed, failed)

        Returns:
            List of session dictionaries, most recent first
        """
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(Session)
            if status:
                query = query.filter(Session.status == status)

            sessions = query.order_by(desc(Session.updated_at)).limit(limit).all()

            return [
                {
                    "id": s.id,
                    "scenario_id": s.scenario_id,
                    "turn": s.turn,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ]
        finally:
            db.close()

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session fields.

        Args:
            session_id: The session's unique identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False if not found

        Note:
            This method updates only the fields provided in the updates dict.
            Use save_session() for complete session replacement.
        """
        db: DBSession = self.SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                for key, value in updates.items():
                    if hasattr(session, key):
                        setattr(session, key, value)  # type: ignore
                session.updated_at = datetime.utcnow()  # type: ignore
                db.commit()
                logger.debug(f"Updated session {session_id}: {list(updates.keys())}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update session: {e}")
            raise
        finally:
            db.close()

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from the database.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if deleted successfully, False if not found
        """
        db: DBSession = self.SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
                logger.info(f"Deleted session {session_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete session: {e}")
            raise
        finally:
            db.close()

    # ==================== UserSettings Operations ====================

    def save_user_settings(self, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save user settings to the database.

        Args:
            settings_dict: Dictionary containing settings data with keys:
                - id: Settings ID (optional, will be generated if not provided)
                - player_name: User's preferred player character name
                - preferences: Additional user preferences as dict (optional)

        Returns:
            Dictionary with saved settings data

        Raises:
            ValueError: If required fields are missing
        """
        db: DBSession = self.SessionLocal()
        try:
            # Check if settings exist (assume single user for now)
            existing = db.query(UserSettings).first()

            if existing:
                # Update existing
                existing.player_name = settings_dict["player_name"]
                existing.preferences = settings_dict.get("preferences", {})
                existing.updated_at = datetime.utcnow()  # type: ignore
                settings = existing
            else:
                # Create new
                settings = UserSettings(
                    player_name=settings_dict["player_name"],
                    preferences=settings_dict.get("preferences", {}),
                    created_at=datetime.utcnow(),
                )
                db.add(settings)

            db.commit()

            result = {
                "id": settings.id,
                "player_name": settings.player_name,
                "preferences": settings.preferences,
                "created_at": (
                    settings.created_at.isoformat() if settings.created_at else None
                ),
                "updated_at": (
                    settings.updated_at.isoformat() if settings.updated_at else None
                ),
            }

            logger.debug(f"Saved user settings for player: {result['player_name']}")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save user settings: {e}")
            raise
        finally:
            db.close()

    def get_user_settings(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve user settings from the database.

        Returns:
            Dictionary containing settings data, or None if not found
        """
        db: DBSession = self.SessionLocal()
        try:
            settings = db.query(UserSettings).first()
            if settings:
                return {
                    "id": settings.id,
                    "player_name": settings.player_name,
                    "preferences": settings.preferences,
                    "created_at": (
                        settings.created_at.isoformat() if settings.created_at else None
                    ),
                    "updated_at": (
                        settings.updated_at.isoformat() if settings.updated_at else None
                    ),
                }
            return None
        finally:
            db.close()

    def update_user_settings(self, updates: Dict[str, Any]) -> bool:
        """
        Update user settings fields.

        Args:
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False if not found
        """
        db: DBSession = self.SessionLocal()
        try:
            settings = db.query(UserSettings).first()
            if settings:
                for key, value in updates.items():
                    if hasattr(settings, key) and key not in ["id", "created_at"]:
                        setattr(settings, key, value)  # type: ignore
                settings.updated_at = datetime.utcnow()  # type: ignore
                db.commit()
                logger.debug(f"Updated user settings: {list(updates.keys())}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update user settings: {e}")
            raise
        finally:
            db.close()
