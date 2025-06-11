from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.schema.password import (
    PasswordResetConfirmSchema,
    PasswordResetResponse,
)
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.base.jwt_helper import JWTGenerator
from ehp.utils import hash_password, constants as const
from ehp.db.db_manager import DBManager
from ehp.core.models.db.authentication import Authentication
from ehp.utils.base import log_error

router = APIRouter(
    tags=["Password Reset"], responses={404: {"description": "Not found"}}
)


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetResponse,  # 1. Using response_model for validation and documentation
    status_code=status.HTTP_200_OK,
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
            user_id = decoded_token["sub"]  # Extract user ID from the token's payload
        except ValueError as e:
            # Raise error if the token is invalid or expired
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or expired token: {e}",
            )

        # 2. Find the user in the database using the decoded user ID
        auth_repo = AuthenticationRepository(session, Authentication)
        auth = await auth_repo.get_by_id(int(user_id))

        if not auth or auth.reset_password != const.AUTH_RESET_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token or reset request.",
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
