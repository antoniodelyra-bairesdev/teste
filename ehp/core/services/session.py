from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from ehp.base.jwt_helper import JWTClaimsPayload
from ehp.base.middleware import authorized_session
from ehp.core.models.db.authentication import Authentication
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.user import UserRepository
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.constants import AUTH_ACTIVE


async def get_authentication(
    request: Request,
    auth_claims: Annotated[JWTClaimsPayload | None, Depends(authorized_session)],
    db_session: ManagedAsyncSession,
) -> Authentication:
    """
    Dependency to get the authenticated user's Authentication object.

    Args:
        request: The HTTP request object.
        auth_claims: The JWT claims payload from the authenticated session.
        db_session: The SQLAlchemy asynchronous session.

    Returns:
        The Authentication object of the authenticated user.
    """
    if auth_claims is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )
    if hasattr(request.state, "user"):
        user: Authentication = request.state.user
    else:
        repository = AuthenticationRepository(db_session)
        user = await repository.get_by_id(int(auth_claims["sub"]))
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )
    if user.is_active != AUTH_ACTIVE:
        raise HTTPException(
            status_code=403,
            detail="User account is not active",
        )
    request.state.user = user
    return user


async def get_user_reading_settings(
    user: Annotated[Authentication, Depends(get_authentication)],
    db_session: ManagedAsyncSession,
) -> dict:
    """
    Dependency to get the authenticated user's reading settings.

    Args:
        user: The authenticated user's Authentication object.
        db_session: The SQLAlchemy asynchronous session.

    Returns:
        Dictionary containing the user's reading settings or default values.
    """
    try:
        user_repo = UserRepository(db_session)
        settings = await user_repo.get_reading_settings(user.user.id)
        return settings
    except Exception:
        # Return default settings if there's any error
        return {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }


AuthContext = Annotated[Authentication, Depends(get_authentication)]
ReadingSettingsContext = Annotated[dict, Depends(get_user_reading_settings)]
