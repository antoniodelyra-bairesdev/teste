from math import floor
import traceback
import secrets
from datetime import datetime, timedelta
import os
from typing import Annotated

from pydantic_core import ValidationError
from sqlalchemy.exc import IntegrityError
import uuid
from io import BytesIO

from ehp.base.jwt_helper import ACCESS_TOKEN_EXPIRE
from ehp.base.session import SessionManager
from ehp.config import settings
from ehp.core.models.schema.user import (
    EmailChangeRequestSchema,
    EmailChangeResponseSchema,
    OnboardingStatusResponseSchema,
    PasswordChangeResponseSchema,
    PasswordChangeSchema,
    UpdatePasswordSchema,
    UpdateUserSettings,
    UserDisplayNameResponseSchema,
    UserDisplayNameUpdateSchema,
    UserProfileResponseSchema,
    UserProfileUpdateSchema,
    AvatarUploadResponseSchema,
)
from fastapi import APIRouter, Body, HTTPException, status, UploadFile, File
from PIL import Image

from ehp.core.repositories.user import UserRepository, UserNotFoundException
from ehp.core.models.schema.user import (
    UserCategoriesUpdateSchema,
    UserCategoriesResponseSchema,
)
from ehp.core.repositories.user import InvalidNewsCategoryException
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.services.session import AuthContext
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.authentication import check_password, hash_password
from ehp.utils.base import log_error, log_info
from ehp.utils.constants import HTTP_INTERNAL_SERVER_ERROR
from ehp.utils.date_utils import timezone_now
from ehp.utils.email import send_notification
from ehp.base.aws import AWSClient


router = APIRouter(
    prefix="/users", tags=["Users"], responses={404: {"description": "Not found"}}
)
non_api_key_router = APIRouter(
    prefix="/users", tags=["Users"], responses={404: {"description": "Not found"}}
)


@router.put(
    "/display-name",
    status_code=status.HTTP_200_OK,
)
async def update_user_display_name(
    display_name_data: UserDisplayNameUpdateSchema,
    session: ManagedAsyncSession,
    current_user: AuthContext,
) -> UserDisplayNameResponseSchema:
    """
    Update user display name.

    This endpoint allows authenticated users to update their display name.
    The display name must be unique across all users and follow the specified format.
    Users can only update their own display name.

    ## Validation Rules

    - **Length**: Between 2 and 150 characters
    - **Characters**: Letters, numbers, hyphens, underscores, and dots only
    - **Spaces**: Not allowed
    - **Uniqueness**: Must be unique across all users
    - **Special characters**: Only hyphens (-), underscores (_), and dots (.) are allowed

    ## Parameters

    - **display_name_data**: The new display name data containing the updated display name
    - **current_user**: The currently authenticated user context
    - **session**: Database session for repository operations

    ## Returns

    `UserDisplayNameResponseSchema` containing:

    - **id**: The user ID
    - **display_name**: The updated display name
    - **message**: Success message (defaults to "Display name updated successfully")

    ## Raises

    - `HTTPException`: 404 if user is not found
    - `HTTPException`: 409 if display name is already taken by another user
    - `HTTPException`: 422 if validation fails (invalid display name format)
    - `HTTPException`: 500 if an internal server error occurs

    ## Example

    **Request:**
    ```
    PUT /users/display-name
    Content-Type: application/json

    {
        "display_name": "JohnDoe"
    }
    ```

    **Response:**
    ```json
    {
        "id": 123,
        "display_name": "JohnDoe",
        "message": "Display name updated successfully"
    }
    ```

    **Error Response (Display name taken):**
    ```json
    {
        "detail": "This display name is already taken"
    }
    ```

    **Error Response (Invalid format):**
    ```json
    {
        "detail": "Display name cannot contain spaces"
    }
    ```
    """
    user_id = None
    try:
        user_id = current_user.user.id
        new_display_name = display_name_data.display_name

        log_info(f"Updating display name for user {user_id} to: {new_display_name}")

        user_repo = UserRepository(session)

        # Get the user first to ensure it exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            log_error(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check if display name is the same (no update needed)
        if user.display_name == new_display_name:
            log_info(f"Display name unchanged for user {user_id}")
            return UserDisplayNameResponseSchema(
                id=user_id,
                display_name=user.display_name,
                message="Display name unchanged (same value provided)",
            )

        # Check if display name already exists (excluding current user)
        if await user_repo.display_name_exists(
            new_display_name, exclude_user_id=user_id
        ):
            log_info(
                f"Display name already exists: {new_display_name} "
                f"(requested by user {user_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This display name is already taken",
            )

        # Update display name and timestamp
        old_display_name = user.display_name
        user.display_name = new_display_name
        user.last_update = timezone_now()

        try:
            await user_repo.update(user)
        except IntegrityError as e:
            # Handle database unique constraint violations
            if (
                "unique constraint" in str(e).lower()
                or "duplicate key" in str(e).lower()
            ):
                log_info(
                    f"Database constraint violation for user {user_id}: "
                    f"display name '{new_display_name}' already exists"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This display name is already taken",
                )
            # Re-raise other integrity errors
            log_error(f"Database integrity error for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database integrity error",
            )

        log_info(
            f"Display name updated successfully for user {user_id}: "
            f"'{old_display_name}' -> '{new_display_name}'"
        )

        return UserDisplayNameResponseSchema(
            id=user_id,
            display_name=user.display_name,
        )

    except ValidationError as ve:
        # Handle Pydantic validation errors with more specific messages
        if ve.errors():
            # Collect all validation error messages
            error_messages = []
            for error in ve.errors():
                error_msg = error.get("msg", "Invalid display name format")
                error_messages.append(error_msg)

            # Join all error messages with semicolons
            error_msg = "; ".join(error_messages)
        else:
            error_msg = "Invalid display name format"

        log_error(
            f"Validation error for user {user_id}: {error_msg} "
            f"(display_name: {display_name_data.display_name if display_name_data else 'None'})"
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception:
        log_error(
            f"Unexpected error updating display name for user {user_id}: "
            f"{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


def generate_email_change_token() -> str:
    """Generate a secure random token for email change."""
    return secrets.token_hex(32)  # 32 bytes = 64 hex characters


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


@router.post("/email-change-request", response_model=EmailChangeResponseSchema)
async def request_email_change(
    request_data: EmailChangeRequestSchema,
    db_session: ManagedAsyncSession,
    user: AuthContext,
) -> EmailChangeResponseSchema:
    """
    Request email change for the authenticated user.
    Generates secure token, stores new email temporarily, and sends verification email.
    """
    try:
        auth_repo = AuthenticationRepository(db_session)

        # Check if new email is different from current
        current_email = user.user_email.lower()
        new_email = request_data.new_email.lower()

        if current_email == new_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New email must be different from current email",
            )

        # Check if new email is already in use by another user
        existing_user = await auth_repo.get_by_email(new_email)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already in use by another account",
            )

        # Generate secure token
        manager = SessionManager()
        change_token = manager.create_session(
            str(user.id),
            new_email,
            with_refresh=False,
        ).access_token

        # Set token expiration (30 minutes from now)
        expiration_time = datetime.now() + timedelta(minutes=30)

        # Update authentication record with pending email and token
        auth = await auth_repo.get_by_id(user.id)
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User authentication not found",
            )

        auth.pending_email = new_email
        auth.email_change_token = change_token
        auth.email_change_token_expires = expiration_time

        _ = await auth_repo.update(auth)

        # Send verification email to NEW email address
        email_subject = "Confirm Your Email Change"
        expiration_minutes = floor(ACCESS_TOKEN_EXPIRE.total_seconds())
        email_body = f"""
        You have requested to change your email address.

        Please click the following link to confirm this change:
        {settings.APP_URL}/users/confirm-email?x-token-auth={change_token}

        This link will expire in {expiration_minutes} minutes.

        If you did not request this change, please ignore this email.
        """

        # Send email to the NEW email address
        success = send_notification(email_subject, email_body, [new_email])

        if not success:
            # If email fails, clear the pending change for security
            auth.pending_email = None
            auth.email_change_token = None
            auth.email_change_token_expires = None
            _ = await auth_repo.update(auth)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email",
            )

        return EmailChangeResponseSchema(
            message="Verification email sent to your new email address",
            code=status.HTTP_200_OK,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error requesting email change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@non_api_key_router.get("/confirm-email", response_model=EmailChangeResponseSchema)
async def confirm_email_change(
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> EmailChangeResponseSchema:
    """
    Confirm email change using the verification token.
    Updates user's email address if token is valid and not expired.
    """
    try:
        auth_repo = AuthenticationRepository(db_session)

        # Check if token is expired
        if (
            not user.email_change_token_expires
            or user.email_change_token_expires < datetime.now()
        ):
            # Clean up expired token
            user.pending_email = None
            user.email_change_token = None
            user.email_change_token_expires = None
            _ = await auth_repo.update(user)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            )

        # Check if pending email exists
        if not user.pending_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending email change found",
            )

        # Update email address
        old_email = user.user_email
        user.user_email = user.pending_email

        # Clear pending change fields
        user.pending_email = None
        user.email_change_token = None
        user.email_change_token_expires = None

        _ = await auth_repo.update(user)

        # Optional: Send confirmation email to old email address
        try:
            confirmation_subject = "Email Address Changed"
            confirmation_body = f"""
            Your email address has been successfully changed from {old_email} to {user.user_email}.

            If you did not make this change, please contact support immediately.
            """
            _ = send_notification(confirmation_subject, confirmation_body, [old_email])
        except Exception as e:
            # Don't fail the email change if confirmation email fails
            log_error(f"Failed to send confirmation email to old address: {e}")

        return EmailChangeResponseSchema(
            message="Email address updated successfully",
            code=status.HTTP_200_OK,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error confirming email change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_settings(
    user: AuthContext,
    db_session: ManagedAsyncSession,
    payload: UpdateUserSettings,
) -> None:
    user_repository = UserRepository(db_session)
    user_record = user.user

    if payload.email_notifications is not None:
        user_record.email_notifications = payload.email_notifications
    if payload.readability_preferences is not None:
        user_record.readability_preferences = payload.readability_preferences
    _ = await user_repository.update(user_record)


@router.post("/me/avatar", response_model=AvatarUploadResponseSchema)
async def upload_avatar(
    db_session: ManagedAsyncSession,
    user: AuthContext,
    avatar: UploadFile = File(...),
) -> AvatarUploadResponseSchema:
    """Upload user avatar image."""

    # File size validation

    # Read file content
    file_content = await avatar.read()

    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 500KB limit",
        )

    # File format validation
    allowed_formats = {".png", ".jpg", ".jpeg", ".webp"}
    file_extension = (
        os.path.splitext(avatar.filename.lower())[1] if avatar.filename else ""
    )
    if file_extension not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG, JPG, JPEG, and WebP formats are allowed",
        )

    # Validate that the file is actually an image
    try:
        image = Image.open(BytesIO(file_content))
        image.verify()
        # Check if format is supported
        if image.format.lower() not in ["png", "jpeg", "webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file"
        )

    try:
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        s3_key = f"avatars/{unique_filename}"

        # Upload to S3
        aws_client = AWSClient()
        aws_client.s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=avatar.content_type,
            ContentDisposition="inline",
        )

        # Generate the avatar URL
        avatar_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION_NAME}.amazonaws.com/{s3_key}"

        # Update user avatar in database
        repository = UserRepository(db_session)
        await repository.update_avatar(user.user.id, avatar_url)

        return AvatarUploadResponseSchema(
            avatar_url=avatar_url, message="Avatar uploaded successfully"
        )

    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        log_error(f"Error uploading avatar: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Failed to upload avatar"
        )


@router.put("/me/settings/categories", response_model=UserCategoriesResponseSchema)
async def update_user_categories(
    categories_data: UserCategoriesUpdateSchema,
    db_session: ManagedAsyncSession,
    user: AuthContext,
) -> UserCategoriesResponseSchema:
    """Update the authenticated user's preferred news categories."""

    try:
        repository = UserRepository(db_session)

        # Update user's preferred news categories
        updated_user = await repository.update_preferred_news_categories(
            user.user.id, categories_data.category_ids
        )

        return UserCategoriesResponseSchema(
            id=updated_user.id,
            full_name=updated_user.full_name,
            preferred_news_categories=updated_user.preferred_news_categories,
        )

    except UserNotFoundException:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except InvalidNewsCategoryException as e:
        await db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        await db_session.rollback()
        raise
    except Exception as e:
        await db_session.rollback()
        log_error(f"Error updating user categories: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get("/me/onboarding-status")
async def get_onboarding_status(
    auth_context: AuthContext,
) -> OnboardingStatusResponseSchema:
    """
    Get the onboarding status of the authenticated user.

    Returns:
        OnboardingStatusResponseSchema: The onboarding status of the user.
    """
    return OnboardingStatusResponseSchema(
        onboarding_complete=auth_context.user.onboarding_complete
    )


@router.put("/me/onboarding-status", status_code=status.HTTP_204_NO_CONTENT)
async def update_onboarding_status(
    auth_context: AuthContext,
    db_session: ManagedAsyncSession,
    onboarding_complete: Annotated[bool, Body(embed=True)],
) -> None:
    """Update the onboarding status of the authenticated user.

    Args:
        auth_context (AuthContext): The authentication context containing user information.
        db_session (ManagedAsyncSession): The database session for repository operations.
        onboarding_status (bool): The new onboarding status to set for the user.

    Returns:
        None: Indicates successful update of the onboarding status.
    """
    repository = UserRepository(db_session)
    user = auth_context.user
    user.onboarding_complete = onboarding_complete
    _ = await repository.update(user)


@router.post("/me/onboarding-status/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_onboarding_status(
    auth_context: AuthContext,
    db_session: ManagedAsyncSession,
) -> None:
    """Reset the onboarding status of the authenticated user.

    Args:
        auth_context (AuthContext): The authentication context containing user information.
        db_session (ManagedAsyncSession): The database session for repository operations.

    Returns:
        None: Indicates successful reset of the onboarding status.
    """
    await update_onboarding_status(
        auth_context=auth_context,
        db_session=db_session,
        onboarding_complete=False,
    )
