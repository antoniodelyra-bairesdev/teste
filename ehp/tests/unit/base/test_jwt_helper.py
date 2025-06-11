from datetime import datetime, timezone, timedelta

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


def test_token_expiration_calculation() -> None:
    """
    Test that token expiration is calculated correctly.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    now = datetime.now(timezone.utc)
    access_exp = jwt_generator.get_expiration(ACCESS_TOKEN_EXPIRE, now)
    refresh_exp = jwt_generator.get_expiration(REFRESH_TOKEN_EXPIRE, now)
    
    assert access_exp > now
    assert refresh_exp > now
    assert refresh_exp > access_exp
    
    # Test default timestamp (current time)
    default_exp = jwt_generator.get_expiration(ACCESS_TOKEN_EXPIRE)
    assert default_exp > datetime.now(timezone.utc)


def test_decode_token_expired() -> None:
    """
    Test decoding an expired token raises ValueError.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    # Create token with past expiration
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    user_id = "test_user"
    email = "test@example.com"
    jti = jwt_generator.generate_jti(user_id, past_time)
    
    # Mock expired token by creating token with past timestamp
    exp = int((past_time - timedelta(seconds=1)).timestamp())
    claims = {
        "sub": user_id,
        "email": email,
        "exp": exp,
        "iss": settings.APP_ISSUER,
        "iat": past_time.timestamp(),
        "jti": jti,
    }
    
    expired_token = jwt_generator.encode_claims(claims)
    
    with pytest.raises(ValueError, match="Token has expired"):
        jwt_generator.decode_token(expired_token, verify_exp=True)


def test_decode_token_invalid_signature() -> None:
    """
    Test decoding a token with invalid signature raises ValueError.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    invalid_generator = JWTGenerator(secret_getter=lambda x: "different_secret")
    
    user_id = "test_user"
    email = "test@example.com"
    token_payload = invalid_generator.generate(user_id, email)
    
    with pytest.raises(ValueError, match="Invalid token"):
        jwt_generator.decode_token(token_payload.access_token, verify_exp=True)


def test_decode_token_malformed() -> None:
    """
    Test decoding a malformed token raises ValueError.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    with pytest.raises(ValueError, match="Invalid token"):
        jwt_generator.decode_token("malformed.token.here", verify_exp=True)


def test_decode_token_skip_expiration() -> None:
    """
    Test decoding token without expiration verification.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    # Create expired token
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    user_id = "test_user"
    email = "test@example.com"
    jti = jwt_generator.generate_jti(user_id, past_time)
    
    exp = int((past_time - timedelta(seconds=1)).timestamp())
    claims = {
        "sub": user_id,
        "email": email,
        "exp": exp,
        "iss": settings.APP_ISSUER,
        "iat": past_time.timestamp(),
        "jti": jti,
    }
    
    expired_token = jwt_generator.encode_claims(claims)
    
    # Should not raise exception when verify_exp=False
    decoded = jwt_generator.decode_token(expired_token, verify_exp=False)
    assert decoded["sub"] == user_id
    assert decoded["email"] == email


def test_validate_jti_invalid() -> None:
    """
    Test JTI validation with invalid JTI.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    user_id = "test_user"
    timestamp = datetime.now(timezone.utc)
    
    # Test with wrong JTI
    assert not jwt_generator.validate_jti("invalid_jti", user_id, timestamp)
    
    # Test with JTI for different user
    valid_jti = jwt_generator.generate_jti(user_id, timestamp)
    assert not jwt_generator.validate_jti(valid_jti, "different_user", timestamp)
    
    # Test with JTI for different timestamp
    different_time = timestamp + timedelta(minutes=1)
    assert not jwt_generator.validate_jti(valid_jti, user_id, different_time)


def test_decode_token_invalid_jti() -> None:
    """
    Test decoding token with invalid JTI raises ValueError.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    user_id = "test_user"
    email = "test@example.com"
    now = datetime.now(timezone.utc)
    
    # Create token with invalid JTI
    exp = int(jwt_generator.get_expiration(ACCESS_TOKEN_EXPIRE, now).timestamp())
    claims = {
        "sub": user_id,
        "email": email,
        "exp": exp,
        "iss": settings.APP_ISSUER,
        "iat": now.timestamp(),
        "jti": "invalid_jti_value",
    }
    
    invalid_token = jwt_generator.encode_claims(claims)
    
    with pytest.raises(ValueError, match="Invalid JTI in token"):
        jwt_generator.decode_token(invalid_token, verify_exp=True)


def test_generate_jti_consistency() -> None:
    """
    Test that JTI generation is consistent for same inputs.
    """
    jwt_generator = JWTGenerator(secret_getter=_mock_secret_getter)
    
    user_id = "test_user"
    timestamp = datetime.now(timezone.utc)
    
    jti1 = jwt_generator.generate_jti(user_id, timestamp)
    jti2 = jwt_generator.generate_jti(user_id, timestamp)
    
    assert jti1 == jti2
    assert isinstance(jti1, str)
    assert len(jti1) == 64  # SHA256 hex digest length


def test_token_payload_model() -> None:
    """
    Test TokenPayload model serialization.
    """
    payload = TokenPayload(
        access_token="test_token",
        refresh_token="test_refresh",
        token_type="Bearer",
        expires_at=3600
    )
    
    # Test model dump with camelCase conversion
    dumped = payload.model_dump(by_alias=True)
    assert dumped["accessToken"] == "test_token"
    assert dumped["refreshToken"] == "test_refresh"
    assert dumped["tokenType"] == "Bearer"
    assert dumped["expiresAt"] == 3600
    
    # Test without refresh token
    payload_no_refresh = TokenPayload(
        access_token="test_token",
        token_type="Bearer",
        expires_at=3600
    )
    
    dumped_no_refresh = payload_no_refresh.model_dump(by_alias=True)
    assert dumped_no_refresh["refreshToken"] is None
