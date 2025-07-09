from fastapi import APIRouter, HTTPException, status

from ehp.base.session import SessionManager
from ehp.core.models.schema.user import (
    PasswordChangeResponseSchema,
    PasswordChangeSchema,
    UpdatePasswordSchema,
    UserProfileResponseSchema,
    UserProfileUpdateSchema,
)
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.user import UserNotFoundException, UserRepository
from ehp.core.services.session import AuthContext
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.authentication import check_password, hash_password
from ehp.utils.base import log_error
from ehp.utils.constants import HTTP_INTERNAL_SERVER_ERROR
from ehp.utils.date_utils import timezone_now

router = APIRouter(prefix="/users", tags=["users"])


@router.put("/me/profile", response_model=UserProfileResponseSchema)
async def update_user_profile(
    profile_data: UserProfileUpdateSchema,
    db_session: ManagedAsyncSession,
    user: AuthContext,
) -> UserProfileResponseSchema:
    """Update the authenticated user's profile information."""

    try:
        repository = UserRepository(db_session)

        # Update user's full name
        updated_user = await repository.update_full_name(
            user.user.id, profile_data.full_name
        )

        return UserProfileResponseSchema(
            id=updated_user.id,
            full_name=updated_user.full_name,
            created_at=updated_user.created_at,
        )

    except UserNotFoundException:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except HTTPException:
        await db_session.rollback()
        raise
    except Exception as e:
        await db_session.rollback()
        log_error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.put("/me/password", response_model=PasswordChangeResponseSchema)
async def change_password(
    password_data: PasswordChangeSchema,
    db_session: ManagedAsyncSession,
    user: AuthContext,
) -> PasswordChangeResponseSchema:
    """Change the authenticated user's password."""

    try:
        auth_repository = AuthenticationRepository(db_session)

        # Get the user's authentication record
        auth = await auth_repository.get_by_id(user.user.auth_id)
        if not auth:
            log_error(f"Authentication record not found for user {user.user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User authentication not found",
            )

        # Verify current password
        if not check_password(auth.user_pwd, password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Hash the new password
        new_password_hash = hash_password(password_data.new_password)

        # Update the password
        success = await auth_repository.update_password(auth.id, new_password_hash)

        if not success:
            log_error(f"Failed to update password for user {user.user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password",
            )

        return PasswordChangeResponseSchema(
            message="Password updated successfully", code=status.HTTP_200_OK
        )

    except HTTPException:
        await db_session.rollback()
        raise
    except Exception as e:
        await db_session.rollback()
        log_error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.put("/password/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_password_by_id(
    user_id: int,
    payload: UpdatePasswordSchema,
    db_session: ManagedAsyncSession,
) -> None:
    """
    Update the password for a user by their ID.

    Args:
        user_id: The ID of the user whose password is to be updated.
        payload: The payload containing the new password and reset token.
        db_session: The SQLAlchemy asynchronous session.

    Returns:
        A JSON response indicating success or failure.

    Raises:
        HTTPException: If the user does not have permission to update the password.
        HTTPException: If the new password is the same as the old password.
    """
    repository = AuthenticationRepository(db_session)
    user = await repository.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.reset_token != payload.reset_token or (
        user.reset_token_expires is not None
        and user.reset_token_expires < timezone_now()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired reset token.",
        )

    # Update the user's password
    if check_password(user.user_pwd, payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="New password cannot be the same as the old password.",
        )
    user.user_pwd = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    _ = await repository.update(user)

    if payload.logout:
        manager = SessionManager()
        # Invalidate all sessions for the user
        manager.wipe_sessions(str(user.id))
