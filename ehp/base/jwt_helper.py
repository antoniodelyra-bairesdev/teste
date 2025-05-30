from datetime import datetime, timedelta, timezone
from typing import Any, cast, Dict

import jwt

from ehp.config import settings


def _get_exp_date() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.SESSION_TIMEOUT)


def _get_exp_date_in_millis() -> float:
    return _get_exp_date().timestamp() * 1000


def simple_encode_token(message: Any) -> str:
    """
    Encode the token to JWT.
    """
    return str(
        jwt.encode(message, settings.ETAI_API_KEY, algorithm=settings.APP_ENCODING_ALG)
    )


def encode_token(message: Dict[str, Any]) -> str:
    """
    Encode the message to JWT(JWS).
    """
    if message:
        message["exp"] = _get_exp_date_in_millis()
        message["iss"] = settings.APP_ISSUER

    return str(
        jwt.encode(message, settings.API_KEY_VALUE, algorithm=settings.APP_ENCODING_ALG)
    )


def decode_token(message: str) -> Dict[str, Any]:
    """
    Decode the JWT with verifying the signature.
    """
    return cast(
        Dict[str, Any],
        jwt.decode(
            message, settings.ETAI_API_KEY, algorithms=[settings.APP_ENCODING_ALG]
        ),
    )
