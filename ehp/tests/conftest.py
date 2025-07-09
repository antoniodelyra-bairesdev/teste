import os

from fakeredis import FakeRedis

os.environ["AWS_ENDPOINT_URL"] = ""
from collections.abc import Generator
from typing import Any, AsyncGenerator, Dict
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from application import app as fastapi_app
from ehp.base.aws import AWSClient
from ehp.base.jwt_helper import JWT_SECRET_NAME
from ehp.config import settings
from ehp.db.db_manager import DBManager
from ehp.db.sqlalchemy_async_connector import Base
from ehp.tests.utils.test_client import EHPTestClient


# Override environment settings for testing when needed
def pytest_configure(config):
    """Configure test environment by loading .env and overriding test-specific settings."""

    # Load .env file first
    load_dotenv()

    # Override only test-specific settings
    os.environ.update(
        {
            "DEBUG": "True",
            "SQLALCHEMY_ECHO": "False",
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "SESSION_COOKIE_NAME": "test_session",
            "API_KEY_VALUE": "test-api-key",
        }
    )


# Create test database engine and tables
@pytest.fixture(scope="session")
async def test_engine():
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get a test session that's rolled back after the test."""

    async with test_engine.connect() as connection:
        asyncsession = sessionmaker(
            connection,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        await connection.run_sync(Base.metadata.create_all)
        async with asyncsession() as session:
            async with session.begin():
                yield session
                await session.rollback()


@pytest.fixture
async def test_db_manager(test_db_session) -> AsyncGenerator[DBManager, None]:
    """Get a test DBManager with a pre-configured session."""
    db_manager = DBManager()

    # Override get_session to return our test session
    original_get_session = db_manager.get_session

    def mock_get_session():
        return test_db_session
    

    db_manager.get_session = mock_get_session
    with patch("ehp.db.DBManager.get_session") as mock_get_db_session:
        mock_get_db_session.return_value = test_db_session
        yield db_manager

    # Restore original method
    db_manager.get_session = original_get_session


# Mock Redis client
@pytest.fixture
def mock_redis():
    return FakeRedis(decode_responses=True)


# FastAPI testing client
@pytest.fixture
def app(test_db_manager) -> FastAPI:
    return fastapi_app


@pytest.fixture
def test_client(
    app: FastAPI,
) -> Generator[EHPTestClient]:
    """Get a TestClient instance with mocked dependencies."""
    client = EHPTestClient(app)
    with client.client:
        yield client


# API Key header fixture
@pytest.fixture
def api_key_header() -> Dict[str, str]:
    return {"X-Api-Key": settings.API_KEY_VALUE}


# Valid auth token header fixture
@pytest.fixture
def auth_token_header() -> Dict[str, str]:
    return {"X-Token-Auth": "test-valid-token"}


# Combined headers fixture
@pytest.fixture
def authenticated_headers(api_key_header, auth_token_header) -> Dict[str, str]:
    return {**api_key_header, **auth_token_header}


# Mock user data
@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    return {
        "id": 1,
        "user_name": "testuser",
        "user_email": "test@example.com",
        "profile_id": 1,
        "is_active": "1",
        "is_confirmed": "1",
        "person": {
            "id": 1,
            "first_name": "Test",
            "last_name": "User",
            "language_id": 1,
        },
    }


# Sample authentication parameters
@pytest.fixture
def sample_auth_params() -> Dict[str, str]:
    return {
        "user_name": "testuser",
        "user_email": "test@example.com",
        "user_pwd": "dGVzdHBhc3N3b3Jk",  # base64 encoded "testpassword"
    }


@pytest.fixture
def aws_mock():
    """
    Fixture to mock AWS services using moto.
    This can be used to mock S3, DynamoDB, etc. as needed.
    """
    with mock_aws():
        yield AWSClient()


@pytest.fixture
@patch("ehp.base.session.get_redis_client", mock_redis)
def setup_jwt(aws_mock: AWSClient):
    """
    Fixture to set up JWT generator with mocked AWS secrets.
    This can be used to test JWT generation and validation.
    """
    _ = aws_mock.secretsmanager_client.create_secret(
        Name=JWT_SECRET_NAME, SecretString=settings.SECRET_KEY
    )
