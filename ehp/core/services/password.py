import secrets
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.base.jwt_helper import JWTGenerator
from ehp.core.models.db.authentication import Authentication
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
        auth_repo = AuthenticationRepository(session, Authentication)
        
        # Find user by email
        auth = await auth_repo.get_by_email(request_data.user_email)
        
        if not auth:
            # For security, don't reveal if email exists or not
            response_json = const.SUCCESS_JSON
        else:
            # Generate secure reset token (32 bytes = 64 hex characters)
            reset_token = secrets.token_hex(32)
            
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
        except ValueError as e:
            # Raise error if the token is invalid or expired
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or expired token: {e}",
            ) from e

        user_id = decoded_token["sub"]  # Extract user ID from the token's payload
        # 2. Find the user in the database using the decoded user ID
        auth_repo = AuthenticationRepository(session, Authentication)
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


"""
async def user_password(
    request: Request,
    pwd_param: PasswordParam,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON

    try:
        from ehp.core.models.db import Authentication

        auth_repo = AuthenticationRepository(session, Authentication)
        auth = await auth_repo.get_by_id(pwd_param.auth_id)

        if auth:
            if auth.user_email != pwd_param.user_email:
                return make_response(const.ERROR_INVALID_EMAIL)

            auth.reset_password = "1"
            auth.reset_code = "1234"  # Generate proper code
            await auth_repo.update(auth)

            response_json = const.SUCCESS_JSON
        else:
            response_json = const.ERROR_USER_DOES_NOT_EXIST

    except Exception as e:
        log_error(e)

    return make_response(response_json)


@router.put("/user/validate/code", response_class=JSONResponse)
async def validate_code(pwd_param: PasswordParam) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON
    try:
        auth_id = pwd_param.auth_id
        reset_code = pwd_param.reset_code
        auth = await Authentication.get_by_id(auth_id)
        if not auth:
            return make_response(const.ERROR_USER_DOES_NOT_EXIST)

        response_json = {"code_is_valid": auth.reset_code == reset_code}

    except Exception as e:
        log_error(e)

    return make_response(response_json)


@router.post("/user/pwd/update", response_class=JSONResponse)
async def update_password(request: Request, pwd_param: PasswordParam) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON
    try:
        email = pwd_param.user_email
        old_password = pwd_param.old_password
        new_password = pwd_param.user_password

        db_manager = request.state.request_config["db_manager"]
        async with db_manager.transaction() as db_session:
            auth = await Authentication.get_by_email(email)
            if not auth:
                response_json = const.ERROR_USER_DOES_NOT_EXIST

            # Check if old password matches the current password
            if not check_password(auth.user_pwd, base64_decrypt(old_password)):
                response_json = const.ERROR_PASSWORD

            # Update password
            auth.user_pwd = hash_password(base64_decrypt(new_password))
            await db_session.flush()
            response_json = const.SUCCESS_JSON

    except Exception as e:
        log_error(e)
    return make_response(response_json)


@router.post("/user/pwd/recover", response_class=JSONResponse)
async def recover_password(
    request: Request,
    auth_param: AuthenticationParam,
) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON
    try:
        email = auth_param.user_email

        db_manager = request.state.request_config["db_manager"]
        async with db_manager.transaction() as db_session:
            auth = await Authentication.get_by_email(email)

            if not auth:
                response_json = const.ERROR_USER_DOES_NOT_EXIST

            if auth.active == const.AUTH_INACTIVE:
                response_json = const.ERROR_USER_DEACTIVATED

            if auth.confirmed != const.AUTH_CONFIRMED:
                response_json = const.ERROR_INVALID_ACCESS

            _random_pwd = random_pwd(8)
            auth.user_pwd = hash_password(_random_pwd)
            auth.reset_password = const.AUTH_RESET_PASSWORD
            try:
                template = await NotificationTemplate.get_by_code(const.NOTI_PASSWORD)
                if template:
                    notification = Notification(
                        template.subject,
                        template.description,
                        template.id,
                        settings.SYS_AUTH_SENDER_ID,
                    )
                    notification.auth_receiver = auth
                    db_session.add(notification)

                    if send_notification(
                        notification.subject,
                        notification.description,
                        auth.user_email,
                        const.NOTI_ROUTE_PASSWORD,
                        _random_pwd,
                    ):
                        notification.sent = const.AUTH_CONFIRMED
                    else:
                        # schedule para re-envio!!!
                        notification.sent = const.AUTH_NOT_CONFIRMED
            except Exception as e:
                log_error(e)

            await db_session.flush()
            response_json = const.SUCCESS_JSON

    except Exception as e:
        log_error(e)
    return make_response(response_json)


@router.put("/user/pwd/reset", response_class=JSONResponse)
async def reset_password(
    request: Request,
    pwd_param: PasswordParam,
) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON
    try:
        auth_id = pwd_param.auth_id
        user_email = pwd_param.user_email
        user_pwd = pwd_param.user_password

        db_manager = request.state.request_config["db_manager"]
        async with db_manager.transaction() as db_session:
            auth = await Authentication.get_by_id(auth_id)
            if auth:
                if auth.user_email != user_email:
                    return make_response(const.ERROR_INVALID_EMAIL)

                if auth.reset_password != "1":
                    return make_response(const.ERROR_UNAUTHORIZED)

                auth.reset_password = "0"
                auth.reset_code = None
                auth.user_pwd = hash_password(base64_decrypt(user_pwd))
                await db_session.flush()

                send_notification(
                    "Password was Reset",
                    (
                        "Your password was just reset. If you did not request this, please"
                        " contact us."
                    ),
                    auth.user_email,
                    "",
                    auth.id,
                )
                response_json = const.SUCCESS_JSON
            else:
                response_json = const.ERROR_USER_DOES_NOT_EXIST
    except Exception as e:
        log_error(e)

    return make_response(response_json)
"""