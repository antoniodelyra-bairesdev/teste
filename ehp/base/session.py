import json
from typing import Any, cast, Dict, Optional
from uuid import uuid4

from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ehp.base.redis_storage import get_redis_client
from ehp.config import settings
from .jwt_helper import encode_token


class SessionData(BaseModel):
    session_id: str
    session_info: Dict[str, Any]


def create_redis_session(session_info: Dict[str, Any]) -> str:
    session_id = str(uuid4().hex)
    session_token = encode_token(message={settings.SESSION_COOKIE_NAME: session_id})
    session_data = SessionData(
        session_id=session_id,
        session_info=session_info,
    )
    write_to_redis_session(session_token, session_data)
    return session_token


def remove_from_redis_session(session_token: str) -> None:
    get_redis_client().delete(session_token)


def get_from_redis_session(session_token: str) -> Optional[Dict[str, Any]]:
    if session_token:
        redis_client = get_redis_client()
        user_session: str = redis_client.get(session_token)
        if user_session:
            redis_client.expire(session_token, settings.SESSION_TIMEOUT)
            return cast(Dict[str, Any], json.loads(user_session))
    return None


def write_to_redis_session(session_token: str, session_data: SessionData) -> None:
    if session_token and session_data:
        redis_client = get_redis_client()
        redis_client.set(session_token, json.dumps(session_data.dict()))
        redis_client.expire(session_token, settings.SESSION_TIMEOUT)


def redirect_to(
    path: Any, status_code: int = 200, headers: Dict[str, Any] = {}
) -> RedirectResponse:
    return RedirectResponse(
        url=path,
        status_code=status_code,
        headers={
            "x-api-key": settings.API_KEY_VALUE,
            **headers,
        },
    )
