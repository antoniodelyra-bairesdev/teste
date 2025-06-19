from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.base.jwt_helper import JWTClaimsPayload
from ehp.base.middleware import authenticated_session
from ehp.core.models.db.authentication import Authentication
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.db.sqlalchemy_async_connector import get_db_session
from ehp.utils.constants import AUTH_ACTIVE


async def get_authentication(
    request: Request,
    auth_claims: Annotated[JWTClaimsPayload, Depends(authenticated_session)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Authentication:
    """
    Dependency to get the authenticated user's claims.

    Args:
        auth_claims: The JWT claims payload from the authenticated session.

    Returns:
        The JWT claims payload of the authenticated user.
    """
    if hasattr(request.state, "user"):
        user: Authentication = request.state.user
    else:
        repository = AuthenticationRepository(db_session, Authentication)
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


AuthContext = Annotated[Authentication, Depends(get_authentication)]
