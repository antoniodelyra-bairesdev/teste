from datetime import datetime, timezone

import pytest
from moto import mock_aws

from ehp.base.aws import AWSClient
from ehp.base.jwt_helper import (
    ACCESS_TOKEN_EXPIRE,
    JWT_SECRET_NAME,
    REFRESH_TOKEN_EXPIRE,
    JWTGenerator,
    TokenPayload,
)
from ehp.config.ehp_core import settings


def _mock_secret_getter(secret_name: str) -> str:
    """
    Mock secret getter function for testing purposes.
    """
    return "mocked_secret_value"


def test_jwt_generator_happy_path() -> None:
    """
    Test the JWTGenerator happy path.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)

    user_id = "test_user"
    email = "test@example.com"
    token_payload = jwt_generator.generate(user_id, email)
    assert isinstance(token_payload, TokenPayload)
    assert token_payload.access_token is not None
    assert token_payload.refresh_token is not None
    assert token_payload.token_type == "Bearer"
    assert token_payload.access_token != token_payload.refresh_token
    # decode call should not raise an exception
    decoded_access_token = jwt_generator.decode_token(token_payload.access_token, True)
    decoded_refresh_token = jwt_generator.decode_token(
        token_payload.refresh_token, True
    )
    assert decoded_access_token is not None
    assert decoded_refresh_token is not None
    assert decoded_access_token != decoded_refresh_token


def test_jwt_generator_invalid_secret() -> None:
    """
    Test the JWTGenerator with an invalid secret.
    """
    jwt_generator = JWTGenerator(secret_getter=lambda x: "invalid_secret_value")
    user_id = "test_user"
    email = "test@example.com"
    validator = JWTGenerator(secret_getter=_mock_secret_getter)

    token = jwt_generator.generate(user_id, email)

    assert token.refresh_token
    with pytest.raises(ValueError):
        validator.decode_token(token.access_token, True)

    with pytest.raises(ValueError):
        validator.decode_token(token.refresh_token, True)


def test_jwt_generator_no_refresh_token() -> None:
    """
    Test the JWTGenerator without generating a refresh token.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)

    user_id = "test_user"
    email = "test@example.com"
    token_payload = jwt_generator.generate(user_id, email, with_refresh=False)
    assert isinstance(token_payload, TokenPayload)
    assert token_payload.access_token is not None
    assert token_payload.refresh_token is None


def test_jti_generation() -> None:
    """
    Test the JTI generation in JWTGenerator.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)

    user_id = "test_user"
    now = datetime.now(timezone.utc)
    jti = jwt_generator.generate_jti(user_id, now)
    assert isinstance(jti, str)
    assert len(jti) > 0
    assert jwt_generator.validate_jti(jti, user_id, now) is True


def test_token_claims() -> None:
    """
    Test the claims in the generated JWT tokens
    match the expected values.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)

    user_id = "test_user"
    email = "test@example.com"
    token_payload = jwt_generator.generate(user_id, email)
    assert token_payload.refresh_token is not None

    decoded_access_token = jwt_generator.decode_token(token_payload.access_token, True)
    decoded_refresh_token = jwt_generator.decode_token(
        token_payload.refresh_token, True
    )
    iat = decoded_access_token.get("iat")
    assert iat is not None
    assert isinstance(iat, float)

    issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)

    assert token_payload.expires_at >= int(
        jwt_generator.get_expiration(
            ACCESS_TOKEN_EXPIRE,
            issued_at,
        ).timestamp()
    )
    assert decoded_access_token == {
        "sub": user_id,
        "email": email,
        "exp": token_payload.expires_at,
        "iss": settings.APP_ISSUER,
        "iat": iat,
        "jti": jwt_generator.generate_jti(user_id, issued_at),
    }
    refresh_token_issued_at = datetime.fromtimestamp(
        decoded_refresh_token["iat"], tz=timezone.utc
    )
    assert decoded_refresh_token["exp"] >= int(
        jwt_generator.get_expiration(
            REFRESH_TOKEN_EXPIRE,
            refresh_token_issued_at,
        ).timestamp()
    )
    assert decoded_refresh_token == {
        "sub": user_id,
        "exp": int(
            jwt_generator.get_expiration(
                REFRESH_TOKEN_EXPIRE, refresh_token_issued_at
            ).timestamp()
        ),
        "iss": settings.APP_ISSUER,
        "iat": decoded_refresh_token["iat"],
        "jti": jwt_generator.generate_jti(user_id, refresh_token_issued_at),
    }


@mock_aws
def test_aws_secret_getter() -> None:
    """
    Test the AWS secret getter function.
    """
    aws_client = AWSClient(endpoint_url="")
    secret_value = "my_secret_value"
    aws_client.secretsmanager_client.create_secret(
        Name=JWT_SECRET_NAME, SecretString=secret_value
    )
    generator = JWTGenerator()

    assert generator.secret == secret_value
