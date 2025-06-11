from fastapi import APIRouter, Depends, Header, HTTPException
from starlette import status

from ehp.base.session import SessionManager
from ehp.core.models.schema.logout import LogoutResponse
from ehp.utils.authentication import needs_api_key
from ehp.utils.base import log_error

router = APIRouter(
    tags=["Authentication"],
    dependencies=[Depends(needs_api_key)],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(x_token_auth: str = Header(...)) -> LogoutResponse:
    """
    Logout the user by invalidating the session token.

    Args:
        x_token_auth: The user's JWT token passed in the request header.

    Returns:
        A successful logout response.
    """
    try:
        session_manager = SessionManager()
        session_manager.remove_session_from_token(x_token_auth)
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
