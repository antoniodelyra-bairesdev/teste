from typing import Annotated, cast, Optional

from fastapi import Header, HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from ehp.base.middleware import get_current_request
from ehp.base.session import get_from_redis_session
from ehp.config import settings
from ehp.utils.base import log_error


async def needs_api_key(x_api_key: Annotated[Optional[str], Header()]) -> None:
    if not x_api_key or x_api_key != settings.API_KEY_VALUE:
        raise HTTPException(status_code=400, detail="Invalid X-Api-Key header.")


async def needs_token_auth(x_token_auth: Annotated[Optional[str], Header()]) -> None:
    if not x_token_auth or not is_valid_token(x_token_auth):
        raise HTTPException(status_code=400, detail="Invalid X-Token-Auth header.")


def hash_password(pwd: str) -> Optional[str]:
    if not pwd:
        raise Exception("Password is required")
    return cast(str, generate_password_hash(pwd, method="scrypt", salt_length=8))


def check_password(pwd_db: str, pwd_form: str) -> bool:
    if pwd_db and pwd_form:
        return cast(bool, check_password_hash(pwd_db, pwd_form))
    return False


def is_valid_token(token_value: str) -> bool:
    try:
        # TODO: Improve this one
        # Needs to check validity...
        return get_from_redis_session(token_value) is not None
    except Exception as err:
        log_error(err)
    return False


def get_language_id() -> int:
    try:
        user_session = get_current_request().state.request_config["user_session"]
        return (
            user_session.get("session_info", {})
            .get("person", {})
            .get("language_id", settings.DEFAULT_LANGUAGE_ID)
        )
    except Exception:
        return (
            get_current_request().state.request_config["language_id"]
            or settings.DEFAULT_LANGUAGE_ID
        )


async def check_es_key(es_key: Annotated[Optional[str], Header()]) -> bool:
    if not es_key or es_key != settings.ES_KEY:
        raise HTTPException(status_code=401, detail="Invalid ES-Key header.")
    return True
