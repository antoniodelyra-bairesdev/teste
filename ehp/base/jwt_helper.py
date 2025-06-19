from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import jwt
from typing import Any, cast, NotRequired, Optional, Tuple, TypedDict

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from ehp.base.aws import AWSClient
from ehp.config.ehp_core import settings


JWT_SECRET_NAME = "EHP_JWT_SECRET"
ACCESS_TOKEN_EXPIRE = timedelta(seconds=settings.SESSION_TIMEOUT)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)


def aws_secret_getter(secret_name: str) -> str:
    """
    Get the secret value from AWS Secrets Manager.
    """
    try:
        aws_client = AWSClient()
        secret_value = aws_client.secretsmanager_client.get_secret_value(
            SecretId=secret_name
        )
        secret: str = secret_value["SecretString"]
    except Exception as e:
        secret = settings.SECRET_KEY
    return secret


class TokenPayload(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: int

    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
    }


class JWTClaimsPayload(TypedDict):
    sub: str  # Subject (user ID)
    email: NotRequired[str]  # User's email
    exp: int  # Expiration time as a Unix timestamp
    iss: str  # Issuer of the token
    iat: float  # Issued at time as a Unix timestamp
    jti: str  # JWT ID, a unique identifier for the token


class JWTGenerator:
    def __init__(self, secret_getter: Callable[[str], str] = aws_secret_getter) -> None:
        """
        Initialize the JWTGenerator with a secret getter function.
        """
        self.secret_getter = secret_getter
        self.secret = self.secret_getter(JWT_SECRET_NAME)

    def get_expiration(
        self, delta: timedelta, timestamp: datetime | None = None
    ) -> datetime:
        """
        Get the expiration date for the token based on the provided delta.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        return timestamp + delta

    def generate(
        self, user_id: str, email: str, with_refresh: bool = True
    ) -> TokenPayload:
        """
        Generate access and refresh tokens for the user.
        """
        now = datetime.now(timezone.utc)
        jti = self.generate_jti(user_id, now)
        access_token, exp = self.encode_access_token(user_id, email, jti, now)
        refresh_token = (
            self.encode_refresh_token(user_id, jti, now) if with_refresh else None
        )

        return TokenPayload(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=exp,
            token_type="Bearer",
        )

    def encode_access_token(
        self, user_id: str, email: str, jti: str, issued_at: datetime
    ) -> Tuple[str, int]:
        """
        Encode the payload into a JWT token.
        """
        exp = int(self.get_expiration(ACCESS_TOKEN_EXPIRE, issued_at).timestamp())
        claims: JWTClaimsPayload = {
            "sub": user_id,
            "email": email,
            "exp": exp,
            "iss": settings.APP_ISSUER,
            "iat": issued_at.timestamp(),
            "jti": jti,
        }

        return self.encode_claims(claims), exp

    def encode_refresh_token(self, user_id: str, jti: str, issued_at: datetime) -> str:
        """
        Encode the payload into a JWT refresh token.
        """
        exp = int(self.get_expiration(REFRESH_TOKEN_EXPIRE, issued_at).timestamp())
        payload: JWTClaimsPayload = {
            "sub": user_id,
            "exp": exp,
            "iss": settings.APP_ISSUER,
            "iat": issued_at.timestamp(),
            "jti": jti,
        }

        return self.encode_claims(payload)

    def encode_claims(self, claims: JWTClaimsPayload) -> str:
        """
        Encode the claims into a JWT token.
        """
        token: str = jwt.encode(
            cast(dict[str, Any], claims),
            self.secret,
            algorithm=settings.APP_ENCODING_ALG,
        )
        return token

    def decode_token(self, token: str, verify_exp: bool) -> JWTClaimsPayload:
        """
        Decode the JWT token and verify its signature.
        """
        try:
            decoded: JWTClaimsPayload = jwt.decode(
                token,
                self.secret,
                algorithms=[settings.APP_ENCODING_ALG],
                options={
                    "verify_exp": verify_exp,
                    "verify_sub": False,  # No need to verify subject in this context
                },
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")
        jti = decoded["jti"]
        user_id = decoded["sub"]
        timestamp = datetime.fromtimestamp(decoded["iat"], timezone.utc)
        if not self.validate_jti(jti, user_id, timestamp):
            raise ValueError("Invalid JTI in token")
        return decoded

    def validate_jti(self, jti: str, user_id: str, timestamp: datetime) -> bool:
        """
        Validate the JTI (JWT ID) to ensure it matches the expected format.
        """
        expected_jti = self.generate_jti(user_id, timestamp)
        return hmac.compare_digest(jti, expected_jti)

    def generate_jti(self, user_id: str, timestamp: datetime) -> str:
        """
        Generate a unique identifier for the JWT token.
        """
        return hmac.new(
            self.secret.encode(),
            f"{user_id}-{timestamp.isoformat()}".encode(),
            hashlib.sha256,
        ).hexdigest()
