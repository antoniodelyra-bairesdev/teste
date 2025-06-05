import os
import pytest
import asyncio
from typing import Any, Dict, Generator, AsyncGenerator
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from ehp.config import settings
from ehp.db.sqlalchemy_async_connector import Base
from ehp.db.db_manager import DBManager
from application import app as fastapi_app
from tests.utils.mocks import MockRedisClient


# Override environment settings for testing when needed
def pytest_configure(config):
    """Configure test environment by loading .env and overriding test-specific settings."""

    # Load .env file first
    load_dotenv()

    # Override only test-specific settings
    os.environ.update({
        "DEBUG": "True",
        "SQLALCHEMY_ECHO": "False",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "SESSION_COOKIE_NAME": "test_session",
        "API_KEY_VALUE": "test-api-key"
    })


# Test database setup and teardown
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    async_session = sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
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

    yield db_manager

    # Restore original method
    db_manager.get_session = original_get_session


# Mock Redis client
@pytest.fixture
def mock_redis():
    return MockRedisClient()


# FastAPI testing client
@pytest.fixture
def app() -> FastAPI:
    return fastapi_app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Get a TestClient instance with mocked dependencies."""
    with TestClient(app) as client:
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
            "language_id": 1
        }
    }


# Sample authentication parameters
@pytest.fixture
def sample_auth_params() -> Dict[str, str]:
    return {
        "user_name": "testuser",
        "user_email": "test@example.com",
        "user_pwd": "dGVzdHBhc3N3b3Jk"  # base64 encoded "testpassword"
    }
