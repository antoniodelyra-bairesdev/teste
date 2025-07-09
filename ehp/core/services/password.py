import secrets
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.base.jwt_helper import JWTGenerator
from ehp.core.models.schema.password import (
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    PasswordResetResponse,
)
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.db.db_manager import DBManager, ManagedAsyncSession
from ehp.utils import constants as const
from ehp.utils import hash_password, make_response, needs_api_key
from ehp.utils.base import log_error
from ehp.utils.email import send_notification

router = APIRouter(
    dependencies=[Depends(needs_api_key)],
    responses={404: {"description": "Not found"}},
)

def generate_reset_token() -> str:
    """
    Generate a secure random token for password reset.
    Returns a hexadecimal string representation of the token.
    """
    return secrets.token_hex(32)  # 32 bytes = 64 hex characters

@router.post("/password-reset/request", response_class=JSONResponse)
async def request_password_reset(
    request_data: PasswordResetRequestSchema,
    session: ManagedAsyncSession,
) -> JSONResponse:
    """
    Request password reset for a user.
    Validates email, generates secure token, stores association with user,
    and triggers password reset email.
    """
    response_json: Dict[str, Any] = const.ERROR_JSON

    try:
        auth_repo = AuthenticationRepository(session)
        
        # Find user by email
        auth = await auth_repo.get_by_email(request_data.user_email)
        
        if not auth:
            # For security, don't reveal if email exists or not
            response_json = const.SUCCESS_JSON
        else:
            # Generate secure reset token (32 bytes = 64 hex characters)
            reset_token = generate_reset_token()
            
            # Set token expiration (30 minutes from now)
            expiration_time = datetime.now() + timedelta(minutes=30)
            
            # Update authentication record with reset token and expiration
            auth.reset_token = reset_token
            auth.reset_token_expires = expiration_time
            auth.reset_password = const.AUTH_RESET_PASSWORD
            
            await auth_repo.update(auth)
            
            # Send password reset email
            email_subject = "Password Reset Request"
            email_body = "You have requested a password reset. Please use the following link to reset your password."
            
            success = send_notification(
                email_subject,
                email_body,
                [auth.user_email],
            )

            if success:
                response_json = const.SUCCESS_JSON
            else:
                # If email fails, clear the token for security
                auth.reset_token = None
                auth.reset_token_expires = None
                auth.reset_password = const.AUTH_INACTIVE
                await auth_repo.update(auth)
                response_json = const.ERROR_JSON

    except Exception as e:
        log_error(e)

    return make_response(response_json)


@router.post(
    "/password-reset/confirm",
    responses={
        400: {"description": "Invalid or expired token"},
        500: {"description": "Internal Server Error"},
    },
)
async def confirm_password_reset(
    params: PasswordResetConfirmSchema,
    session: AsyncSession = Depends(DBManager),  # Kept for commit/rollback management
) -> PasswordResetResponse:
    """
    Confirm a password reset using a token and update the user's password.

    Args:
        params: Contains reset token and new password.
        session: Database session.

    Returns:
        PasswordResetResponse with success/error status
    """
    try:
        # 1. Decode and validate the reset token using JWTGenerator
        jwt_helper = JWTGenerator()
        try:
            # Decode the token and check if it is valid and not expired
            decoded_token = jwt_helper.decode_token(params.token, verify_exp=True)
        except ValueError as e:
            # Raise error if the token is invalid or expired
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or expired token: {e}",
            ) from e

        user_id = decoded_token["sub"]  # Extract user ID from the token's payload
        # 2. Find the user in the database using the decoded user ID
        auth_repo = AuthenticationRepository(session)
        auth = await auth_repo.get_by_id(int(user_id))

        if not auth or auth.reset_password != const.AUTH_RESET_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token or reset request.",
            )

        if auth.reset_token_expires < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reset token has expired or is not active.",
            )

        # 3. Update the user's password
        new_password = params.new_password
        auth.user_pwd = hash_password(new_password)

        # 4. Invalidate the reset token (set reset_password to 0)
        auth.reset_password = "0"
        auth.reset_code = None  # Clear the reset code

        await auth_repo.update(auth)  # Save the changes to the database

        # Return a success response
        return PasswordResetResponse(
            message="Password has been reset successfully.", code=status.HTTP_200_OK
        )

    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions to be handled by FastAPI
    except Exception as e:
        log_error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while updating the password.",
        )
