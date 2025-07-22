from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.services.session import get_user_reading_settings
from ehp.db.db_manager import ManagedAsyncSession


@pytest.mark.unit
class TestGetUserReadingSettings:
    """Unit tests for get_user_reading_settings dependency."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Create a mock ManagedAsyncSession."""
        return AsyncMock(spec=ManagedAsyncSession)

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock User instance."""
        return User(
            id=123,
            full_name="Test User",
            display_name="testuser",
            auth_id=456,
        )

    @pytest.fixture
    def mock_authentication(self, mock_user: User) -> Authentication:
        """Create a mock Authentication instance."""
        auth = MagicMock(spec=Authentication)
        auth.user = mock_user
        return auth

    @pytest.fixture
    def sample_reading_settings(self) -> dict:
        """Sample reading settings."""
        return {
            "font_size": "Large",
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
            "font_weight": "Bold",
            "line_spacing": "Wide",
            "color_mode": "Dark",
        }

    async def test_get_user_reading_settings_success(
        self, mock_db_session: AsyncMock, mock_authentication: Authentication, sample_reading_settings: dict
    ):
        """Test successful reading settings retrieval."""
        with patch("ehp.core.services.session.UserRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_reading_settings = AsyncMock(return_value=sample_reading_settings)

            result = await get_user_reading_settings(mock_authentication, mock_db_session)

            assert result == sample_reading_settings
            mock_repo.get_reading_settings.assert_called_once_with(mock_authentication.user.id)

    async def test_get_user_reading_settings_repository_error(
        self, mock_db_session: AsyncMock, mock_authentication: Authentication
    ):
        """Test reading settings retrieval when repository raises an exception."""
        with patch("ehp.core.services.session.UserRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_reading_settings = AsyncMock(side_effect=Exception("Database error"))

            result = await get_user_reading_settings(mock_authentication, mock_db_session)

            # Should return default settings when error occurs
            expected_defaults = {
                "font_size": "Medium",
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }
            assert result == expected_defaults

    async def test_get_user_reading_settings_user_not_found_error(
        self, mock_db_session: AsyncMock, mock_authentication: Authentication
    ):
        """Test reading settings retrieval when user not found."""
        with patch("ehp.core.services.session.UserRepository") as mock_repo_class:
            from ehp.core.repositories.user import UserNotFoundException
            
            mock_repo = mock_repo_class.return_value
            mock_repo.get_reading_settings = AsyncMock(
                side_effect=UserNotFoundException("User not found")
            )

            result = await get_user_reading_settings(mock_authentication, mock_db_session)

            # Should return default settings when user not found
            expected_defaults = {
                "font_size": "Medium",
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }
            assert result == expected_defaults

    async def test_get_user_reading_settings_returns_defaults_on_any_exception(
        self, mock_db_session: AsyncMock, mock_authentication: Authentication
    ):
        """Test that any exception returns default settings."""
        with patch("ehp.core.services.session.UserRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            # Test different types of exceptions
            exceptions_to_test = [
                ValueError("Invalid value"),
                RuntimeError("Runtime error"),
                ConnectionError("Connection failed"),
                Exception("Generic error"),
            ]

            for exception in exceptions_to_test:
                mock_repo.get_reading_settings = AsyncMock(side_effect=exception)

                result = await get_user_reading_settings(mock_authentication, mock_db_session)

                expected_defaults = {
                    "font_size": "Medium",
                    "fonts": {"headline": "System", "body": "System", "caption": "System"},
                    "font_weight": "Normal",
                    "line_spacing": "Standard",
                    "color_mode": "Default",
                }
                assert result == expected_defaults

    async def test_get_user_reading_settings_uses_correct_user_id(
        self, mock_db_session: AsyncMock, mock_authentication: Authentication, sample_reading_settings: dict
    ):
        """Test that the correct user ID is passed to the repository."""
        with patch("ehp.core.services.session.UserRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_reading_settings = AsyncMock(return_value=sample_reading_settings)

            await get_user_reading_settings(mock_authentication, mock_db_session)

            # Verify the correct user ID was used
            mock_repo.get_reading_settings.assert_called_once_with(mock_authentication.user.id)
            assert mock_authentication.user.id == 123  # From mock_user fixture 