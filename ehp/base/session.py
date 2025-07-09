from typing import Any, Dict, cast

import redis
from pydantic import BaseModel

from ehp.base.jwt_helper import JWTClaimsPayload, JWTGenerator, TokenPayload
from ehp.base.redis_storage import get_redis_client
from ehp.config import settings

# from .jwt_helper import encode_token # removed import until token endpoint is implemented


class SessionData(BaseModel):
    session_id: str
    session_token: str
    metadata: Dict[str, Any]  # Optional jsonable metadata for session


class SessionManager:
    def __init__(
        self,
        jwt_generator: JWTGenerator | None = None,
        redis_client: redis.Redis | None = None,
    ) -> None:
        """
        Initialize the SessionManager with a JWT generator and Redis client.
        If no JWT generator is provided, a default one is created.
        If no Redis client is provided, the default Redis client is used.
        """
        self.jwt_generator = jwt_generator or JWTGenerator()
        self.redis_client = redis_client or get_redis_client()

    def create_session(
        self, user_id: str, email: str, with_refresh: bool = True
    ) -> TokenPayload:
        """
        Create a new session for the user with the given user_id and email.
        If with_refresh is True, a refresh token will be included in the session.
        """
        token_payload = self.jwt_generator.generate(user_id, email, with_refresh)
        session_id = self._get_id_from_token(token_payload.access_token)
        data = SessionData(
            session_id=session_id, session_token=token_payload.access_token, metadata={}
        )
        self._save_session(user_id, session_id, data)
        return token_payload

    def _get_claims(self, token: str) -> JWTClaimsPayload:
        """
        Decode the JWT token to get the claims.
        This is used internally to extract user_id and other claims.
        """
        return self.jwt_generator.decode_token(token, verify_exp=True)

    def _get_id_from_token(self, token: str) -> str:
        claims = self.jwt_generator.decode_token(token, verify_exp=False)
        return claims["jti"]

    def _save_session(
        self, user_id: str, session_id: str, session_data: SessionData
    ) -> None:
        """
        Save the session data to Redis.
        """
        _ = self.redis_client.set(session_id, session_data.model_dump_json())
        _ = self.redis_client.hset(user_id, session_id, session_data.session_token)
        _ = self.redis_client.expire(session_id, settings.SESSION_TIMEOUT)

    def get_session_from_token(self, token: str) -> SessionData | None:
        """
        Retrieve the session data from Redis using the session_id.
        Returns None if the session does not exist.
        """
        session_id = self._get_id_from_token(token)
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> SessionData | None:
        session_data_json = cast(str, self.redis_client.get(session_id))
        if session_data_json:
            _ = self.redis_client.expire(session_id, settings.SESSION_TIMEOUT)
            return SessionData.model_validate_json(session_data_json)
        else:
            return None

    def remove_session_from_token(self, token: str) -> None:
        """
        Remove the session data from Redis using the token.
        """
        claims = self._get_claims(token)
        user_id = claims["sub"]
        session_id = claims["jti"]
        self.remove_session(user_id, session_id)

    def remove_session(self, user_id: str, session_id: str) -> None:
        """
        Remove the session data from Redis using the session_id.
        """
        _ = self.redis_client.delete(session_id)
        _ = self.redis_client.hdel(user_id, session_id)

    def wipe_sessions(self, user_id: str) -> None:
        """
        Wipe all sessions for a given user_id.
        """
        session_ids = cast(Dict[str, Any], self.redis_client.hgetall(user_id))
        for session_id in session_ids:
            _ = self.redis_client.delete(session_id)
        _ = self.redis_client.delete(user_id)
