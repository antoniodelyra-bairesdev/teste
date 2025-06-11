from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.base import create_redis_session
from ehp.core.models.schema import AuthenticationSchema
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.base.dependencies import get_session
from ehp.utils import check_password, make_response
from ehp.utils import constants as const
from ehp.utils.base import base64_decrypt, log_error

auth_router = APIRouter()


@auth_router.post("/authenticate", response_class=JSONResponse)
async def authenticate(
    request: Request,
    auth_param: AuthenticationParam,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON

    try:
        # Import model here to avoid circular imports
        from ehp.core.models.db import Authentication

        # Use repository instead of direct model access
        auth_repo = AuthenticationRepository(session, Authentication)

        email = auth_param.user_email
        username = auth_param.user_name

        # Repository calls instead of model methods
        auth: Optional[Any] = None
        if email:
            auth = await auth_repo.get_by_email(email)

        if not auth and username:
            auth = await auth_repo.get_by_username(username)

        if not auth:
            response_json = const.ERROR_USER_DOES_NOT_EXIST
        else:
            # Rest of authentication logic remains the same
            if auth.is_active == const.AUTH_INACTIVE:
                response_json = const.ERROR_USER_DEACTIVATED
            elif auth.is_confirmed == const.AUTH_CONFIRMED and check_password(
                auth.user_pwd, base64_decrypt(auth_param.user_pwd)
            ):
                auth_json = await auth.to_dict()
                session_token = create_redis_session(auth_json)

                response_json = {
                    "session_token": session_token,
                    **auth_json,
                }
            else:
                response_json = const.ERROR_PASSWORD

    except Exception as e:
        log_error(e)

    return make_response(response_json)
