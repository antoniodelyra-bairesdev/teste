from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from ehp.base.jwt_helper import JWTClaimsPayload
from ehp.base.middleware import authenticated_session, authorized_session
from ehp.base.session import SessionManager
from ehp.core.models.schema.logout import LogoutResponse
from ehp.utils.base import log_error

router = APIRouter(
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)


@router.post("/logout")
async def logout(
    x_token_auth: Annotated[JWTClaimsPayload | None, Depends(authorized_session)],
) -> LogoutResponse:
    """
    Logout the user by invalidating the session token.

    Args:
        x_token_auth: The user's JWT token passed in the request header.

    Returns:
        A successful logout response.
    """
    if x_token_auth is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
        )
    try:
        session_manager = SessionManager()
        session_manager.remove_session(x_token_auth["sub"], x_token_auth["jti"])
        return LogoutResponse(
            message="Logged out successfully",
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        log_error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout",
        )
