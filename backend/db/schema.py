"""
Database schema definitions using SQLAlchemy.

This module defines the database tables for storing scenarios and game sessions.
All data is stored in a single SQLite database file for easy backup and portability.
"""

# mypy: ignore-errors

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()  # type: ignore


class Scenario(Base):
    """
    Scenario table storing generated scenario specifications.

    Attributes:
        id: Unique scenario identifier (UUID)
        name: Human-readable scenario name
        spec: Complete ScenarioSpec as JSON
        status: Scenario status (generated, compiled, failed)
        created_at: Timestamp when scenario was created
        updated_at: Timestamp when scenario was last modified
    """

    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    spec = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="generated")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Session(Base):
    """
    Session table storing active game sessions.

    Attributes:
        id: Unique session identifier (UUID)
        scenario_id: Reference to the scenario this session uses
        seed: Random seed for reproducibility
        state: Current game state as JSON
        turn: Current turn number
        turn_history: Array of turn records as JSON
        world_background: Generated world narrative
        entities: Current entity/character list as JSON
        private_memory: Private entity memories as JSON
        public_memory: Public entity memories as JSON
        scenario_spec: Cached scenario spec for performance (optional)
        status: Session status (active, completed, failed)
        created_at: Timestamp when session was created
        updated_at: Timestamp when session was last updated
    """

    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    scenario_id = Column(String, nullable=False)
    seed = Column(Integer, nullable=True)
    state = Column(JSON, nullable=False)
    turn = Column(Integer, nullable=False, default=0)
    turn_history = Column(JSON, nullable=False, default=list)
    world_background = Column(Text, nullable=True)
    entities = Column(JSON, nullable=False, default=list)
    private_memory = Column(JSON, nullable=False, default=dict)
    public_memory = Column(JSON, nullable=False, default=dict)
    scenario_spec = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserSettings(Base):
    """
    UserSettings table storing user preferences and configuration.

    Attributes:
        id: Unique settings identifier (UUID)
        player_name: User's preferred player character name
        preferences: Additional user preferences as JSON
        created_at: Timestamp when settings were created
        updated_at: Timestamp when settings were last modified
    """

    __tablename__ = "user_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_name = Column(String, nullable=False)
    preferences = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
