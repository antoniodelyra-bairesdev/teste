from typing import Annotated, Optional, cast

from fastapi import Header, HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from ehp.base.session import SessionManager
from ehp.config import settings
from ehp.utils.base import log_error


def needs_api_key(x_api_key: Annotated[Optional[str], Header()]) -> None:
    if not x_api_key or x_api_key != settings.API_KEY_VALUE:
        raise HTTPException(status_code=400, detail="Invalid X-Api-Key header.")


async def needs_token_auth(x_token_auth: Annotated[Optional[str], Header()]) -> None:
    if not x_token_auth or not is_valid_token(x_token_auth):
        raise HTTPException(status_code=400, detail="Invalid X-Token-Auth header.")


def hash_password(pwd: str) -> str:
    if not pwd:
        raise Exception("Password is required")
    return generate_password_hash(pwd, method="scrypt", salt_length=8)


def check_password(pwd_db: str, pwd_form: str) -> bool:
    if pwd_db and pwd_form:
        return cast(bool, check_password_hash(pwd_db, pwd_form))
    return False


def is_valid_token(token_value: str) -> bool:
    try:
        session_manager = SessionManager()
        session_data = session_manager.get_session_from_token(token_value)
        if not session_data:
            return False
        try:
            session_manager.jwt_generator.decode_token(token_value, verify_exp=True)
        except ValueError:
            # value error means the token is invalid or expired
            return False
    except Exception as err:
        log_error(err)
        return False
    else:
        return True


async def check_es_key(es_key: Annotated[Optional[str], Header()]) -> bool:
    if not es_key or es_key != settings.ES_KEY:
        raise HTTPException(status_code=401, detail="Invalid ES-Key header.")
    return True
