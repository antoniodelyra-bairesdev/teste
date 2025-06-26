from datetime import datetime
from typing import NoReturn

from fastapi import APIRouter, HTTPException
from starlette import status

from ehp.base.jwt_helper import TokenPayload
from ehp.base.session import SessionManager
from ehp.config.ehp_core import settings
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.schema.token import TokenRequestData
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.authentication import check_password
from ehp.utils.base import log_error, log_info
from ehp.utils.constants import AUTH_ACTIVE

router = APIRouter(
    tags=["Authentication"], responses={404: {"description": "Not found"}}
)


async def _count_failures(
    repository: AuthenticationRepository,
    user: Authentication,
    detail: str,
    status_code: int,
) -> NoReturn:
    """
    Helper function to handle account failure scenarios.

    This function updates the user's retry count and last login attempt,
    then raises an HTTPException with the provided detail and status code.

    The JSON Payload is something like:
    {
        "detail": {
            "detail": "Invalid credentials",
            "retry_count": 1,
            "left_attempts": 4
        }
    }
    """
    user.retry_count += 1
    user.last_login_attempt = datetime.now()
    await repository.update(user)

    raise HTTPException(
        status_code=status_code,
        detail={
            "detail": detail,
            "retry_count": user.retry_count,
            "left_attempts": max(0, settings.LOGIN_ERROR_MAX_RETRY - user.retry_count),
        },
    )


@router.post("/token", status_code=status.HTTP_200_OK, response_model_by_alias=False)
async def login_for_access_token(
    token_data: TokenRequestData,
    session: ManagedAsyncSession,
) -> TokenPayload:
    """
    OAuth 2.0 Password Grant Flow - Authenticate User and Generate JWT

    This endpoint implements the OAuth 2.0 password grant flow to authenticate users.
    It accepts a username (or email) and a password, validates the credentials,
    and returns a JWT access token upon successful authentication.

    The password grant flow is typically used by client applications (such as mobile apps)
    that directly collect user credentials and exchange them for an access token.

    **Parameters:**
    - `username` (str): The username or email of the user trying to authenticate.
    - `password` (str): The plain text password of the user.

    **Responses:**
    - **200 OK**: Returns a JWT access token, the token type (bearer), and its expiration time in seconds.
    - **400 Bad Request**: Missing username or password.
    - **401 Unauthorized**: Invalid credentials, deactivated account, or unconfirmed account.
    - **500 Internal Server Error**: An error occurred while processing the request.

    **Response Model:**
    - `access_token` (str): The generated JWT access token.
    - `token_type` (str): The type of the token (typically "bearer").
    - `expires_in` (int): The token expiration time in seconds.
    """
    username = token_data.username
    password = token_data.password

    log_info(f"Received login attempt with username: {username}")

    if not username or not password:
        log_error("Login attempt failed: Missing username or password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    # Get DB session
    auth_repo = AuthenticationRepository(session, Authentication)

    # Try by email, fallback to username
    log_info(f"Attempting to retrieve user by email: {username}")
    user = await auth_repo.get_by_email(username)
    if not user:
        log_info(f"User not found by email, trying username: {username}")
        user = await auth_repo.get_by_username(username)

    if not user:
        log_error(
            f"Login attempt failed: User not found for username/email: {username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    log_info(f"User found: {user.id} - {user.user_email}")

    if user.retry_count >= settings.LOGIN_ERROR_MAX_RETRY:
        # If retry count exceeds max, raise an error
        timedelta_to_wait = (
            settings.LOGIN_ERROR_TIMEOUT
            - (datetime.now() - user.last_login_attempt).total_seconds()
        )
        if timedelta_to_wait > 0:
            log_error(
                f"Account locked for user {user.id} due to"
                + " too many failed login attempts"
                + f" (retry_count: {user.retry_count}, wait_time: {timedelta_to_wait} seconds)"
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "detail": "Account locked due to too many failed login attempts",
                    "retry_count": user.retry_count,
                    "wait_time": timedelta_to_wait,
                },
            )
        else:
            log_info(
                f"Retry count exceeded for user {user.id}, but lockout period has passed."
                + " Resetting retry count."
            )
            # Reset retry count if the lockout period has passed
            user.retry_count = 0
            user.last_login_attempt = datetime.now()
            await auth_repo.update(user)

    # Check account status (active and confirmed)
    if user.is_active != AUTH_ACTIVE:
        log_error(f"Account is deactivated for user {user.id} - {user.user_email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    # Commented out for now, but can be used if account confirmation is required
    # if user.is_confirmed != AUTH_CONFIRMED:
    #     log_error(f"Account is not confirmed for user {user.id} - {user.user_email}")
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Account is not confirmed",
    #     )

    # Verify password (with hash)
    if not check_password(user.user_pwd, password):
        log_error(
            f"Invalid credentials for user {user.id} - {user.user_email}"
            + f" (retry_count: {user.retry_count})"
        )
        await _count_failures(
            repository=auth_repo,
            user=user,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Use SessionManager to create a session and token
    log_info(f"User {user.id} - {user.user_email} authenticated successfully")
    session_manager = SessionManager()
    token_payload = session_manager.create_session(
        user_id=str(user.id), email=user.user_email, with_refresh=False
    )
    log_info(
        f"Generated token for user {user.id} - {user.user_email},"
        + f" expires in {token_payload.expires_at} seconds"
    )
    return token_payload
