from unittest.mock import Mock, call

import pytest
from moto import mock_aws

from ehp.base.jwt_helper import JWTGenerator
from ehp.base.session import SessionData, SessionManager
from ehp.config.ehp_core import settings


def _mock_secret_getter(secret_name: str) -> str:
    """
    Mock secret getter function for testing purposes.
    """
    return "mocked_secret_value"


@pytest.fixture
def jwt_generator():
    """
    Fixture to provide a JWTGenerator instance with a mocked secret getter.
    """
    return JWTGenerator(secret_getter=_mock_secret_getter)


@mock_aws
def test_create_session(jwt_generator) -> None:
    redis_client = Mock()
    session_manager = SessionManager(
        jwt_generator=jwt_generator, redis_client=redis_client
    )

    user_id = "test_user"
    email = "test@example.com"
    token_payload = session_manager.create_session(user_id, email)
    jti = session_manager._get_id_from_token(token_payload.access_token)

    assert token_payload.access_token is not None
    assert token_payload.refresh_token is not None
    redis_client.set.assert_called_once_with(
        jti,
        SessionData(
            session_id=jti, session_token=token_payload.access_token, metadata={}
        ).model_dump_json(),
    )
    redis_client.expire.assert_called_once_with(jti, settings.SESSION_TIMEOUT)


@mock_aws
def test_get_session_from_token(jwt_generator) -> None:
    redis_client = Mock()
    session_manager = SessionManager(
        jwt_generator=jwt_generator, redis_client=redis_client
    )

    user_id = "test_user"
    email = "test@example.com"
    token_payload = session_manager.create_session(user_id, email)
    redis_client.get.return_value = SessionData(
        session_id=session_manager._get_id_from_token(token_payload.access_token),
        session_token=token_payload.access_token,
        metadata={},
    ).model_dump_json()
    session_data = session_manager.get_session_from_token(token_payload.access_token)
    jti = session_manager._get_id_from_token(token_payload.access_token)

    assert session_data is not None
    assert session_data.session_id == jti
    assert session_data.session_token == token_payload.access_token
    redis_client.get.assert_called_once_with(jti)
    redis_client.expire.assert_has_calls(
        (call(jti, settings.SESSION_TIMEOUT), call(jti, settings.SESSION_TIMEOUT))
    )


@mock_aws
def test_remove_session_from_token(jwt_generator) -> None:
    redis_client = Mock()
    session_manager = SessionManager(
        jwt_generator=jwt_generator, redis_client=redis_client
    )

    user_id = "test_user"
    email = "test@example.com"
    token_payload = session_manager.create_session(user_id, email)
    jti = session_manager._get_id_from_token(token_payload.access_token)
    session_manager.remove_session_from_token(token_payload.access_token)

    redis_client.delete.assert_called_once_with(jti)
