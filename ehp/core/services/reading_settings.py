from fastapi import APIRouter, Depends, HTTPException, status

from ehp.core.models.schema.reading_settings import (
    ReadingSettings,
    ReadingSettingsUpdate,
)
from ehp.core.repositories.user import UserNotFoundException, UserRepository
from ehp.core.services.session import AuthContext
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.authentication import needs_api_key

router = APIRouter(
    prefix="/users",
    tags=["Reading Settings"],
    dependencies=[Depends(needs_api_key)],
    responses={404: {"description": "Not found"}},
)


@router.get("/reading-settings")
async def get_reading_settings(
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> ReadingSettings:
    """Get user's reading settings."""
    try:
        repository = UserRepository(db_session)
        settings_dict = await repository.get_reading_settings(user.user.id)
        return ReadingSettings(**settings_dict)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/reading-settings", status_code=status.HTTP_201_CREATED)
async def create_reading_settings(
    settings: ReadingSettings,
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> ReadingSettings:
    """Create/overwrite user's reading settings."""
    try:
        repository = UserRepository(db_session)
        await repository.update_reading_settings(user.user.id, settings.model_dump())
        return settings
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.put("/reading-settings")
async def update_reading_settings(
    settings_update: ReadingSettingsUpdate,
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> ReadingSettings:
    """Update user's reading settings (merge with existing)."""
    try:
        repository = UserRepository(db_session)

        # Get current settings
        current_settings = await repository.get_reading_settings(user.user.id)
        new_settings = current_settings.copy()

        # Merge update with current settings
        updated_data = settings_update.model_dump(exclude_unset=True)
        new_settings.update(updated_data)

        # Save merged settings
        await repository.update_reading_settings(user.user.id, new_settings)

        return ReadingSettings(**new_settings)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
