"""
Settings API endpoints for managing user preferences.

This module provides REST API endpoints for creating, reading, and updating
user settings including player name and preferences.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SettingsRequest(BaseModel):
    """Request model for user settings operations."""

    player_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Player's preferred character name",
    )
    preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional user preferences"
    )


class SettingsResponse(BaseModel):
    """Response model for user settings operations."""

    id: str
    player_name: str
    preferences: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]


@router.get("/", response_model=SettingsResponse)
async def get_user_settings():
    """
    Get current user settings.

    Returns:
        Current user settings or 404 if not found
    """
    try:
        db_manager = DatabaseManager(settings.database_path)
        settings_data = db_manager.get_user_settings()

        if not settings_data:
            raise HTTPException(status_code=404, detail="User settings not found")

        return SettingsResponse(**settings_data)
    except Exception as e:
        logger.error(f"Failed to get user settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=SettingsResponse)
async def create_user_settings(request: SettingsRequest):
    """
    Create or update user settings.

    Args:
        request: Settings data including player name and preferences

    Returns:
        Created/updated settings data
    """
    try:
        db_manager = DatabaseManager(settings.database_path)

        settings_dict = {
            "player_name": request.player_name,
            "preferences": request.preferences or {},
        }

        result = db_manager.save_user_settings(settings_dict)

        logger.info(f"✓ User settings saved for player: {request.player_name}")
        return SettingsResponse(**result)
    except Exception as e:
        logger.error(f"Failed to save user settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/", response_model=SettingsResponse)
async def update_user_settings(request: SettingsRequest):
    """
    Update existing user settings.

    Args:
        request: Updated settings data

    Returns:
        Updated settings data
    """
    try:
        db_manager = DatabaseManager(settings.database_path)

        # Check if settings exist
        existing = db_manager.get_user_settings()
        if not existing:
            raise HTTPException(status_code=404, detail="User settings not found")

        updates = {
            "player_name": request.player_name,
            "preferences": request.preferences or {},
        }

        success = db_manager.update_user_settings(updates)
        if not success:
            raise HTTPException(status_code=404, detail="User settings not found")

        # Return updated settings
        updated_settings = db_manager.get_user_settings()
        if not updated_settings:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve updated settings"
            )

        logger.info(f"✓ User settings updated for player: {request.player_name}")
        return SettingsResponse(**updated_settings)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
