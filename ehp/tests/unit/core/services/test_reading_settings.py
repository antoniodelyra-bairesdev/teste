import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch

from ehp.core.models.schema.reading_settings import ReadingSettings, ReadingSettingsUpdate
from ehp.core.services.reading_settings import (
    get_reading_settings,
    create_reading_settings,
    update_reading_settings,
)
from ehp.core.repositories.user import UserRepository, UserNotFoundException


@pytest.mark.unit
class TestReadingSettingsServices:
    """Unit tests for reading settings service functions."""

    @pytest.fixture
    def mock_user_context(self):
        """Mock user context."""
        mock_context = MagicMock()
        mock_context.user.id = 123
        return mock_context

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository instance."""
        with patch('ehp.core.services.reading_settings.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock(spec=UserRepository)
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    async def test_get_reading_settings_success(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test successful get reading settings."""
        # Arrange
        expected_settings = {
            "font_size": "Large",
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
            "font_weight": "Bold",
            "line_spacing": "Wide",
            "color_mode": "Dark",
        }
        mock_user_repo.get_reading_settings.return_value = expected_settings

        # Act
        result = await get_reading_settings(mock_user_context, mock_db_session)

        # Assert
        assert isinstance(result, ReadingSettings)
        assert result.font_size == "Large"
        assert result.fonts.headline == "Arial"
        assert result.color_mode == "Dark"
        mock_user_repo.get_reading_settings.assert_called_once_with(123)

    async def test_get_reading_settings_with_defaults(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test get reading settings returns defaults when none exist."""
        # Arrange
        default_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }
        mock_user_repo.get_reading_settings.return_value = default_settings

        # Act
        result = await get_reading_settings(mock_user_context, mock_db_session)

        # Assert
        assert isinstance(result, ReadingSettings)
        assert result.font_size == "Medium"
        assert result.fonts.headline == "System"
        assert result.color_mode == "Default"

    async def test_create_reading_settings_success(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test successful create reading settings."""
        # Arrange
        new_settings = ReadingSettings(
            font_size="Small",
            fonts={"headline": "Times", "body": "Helvetica", "caption": "Arial"},
            font_weight="Light",
            line_spacing="Compact",
            color_mode="Light",
        )
        mock_user_repo.update_reading_settings.return_value = MagicMock()

        # Act
        result = await create_reading_settings(new_settings, mock_user_context, mock_db_session)

        # Assert
        assert isinstance(result, ReadingSettings)
        assert result.font_size == "Small"
        assert result.fonts.headline == "Times"
        mock_user_repo.update_reading_settings.assert_called_once_with(
            123, new_settings.model_dump()
        )

    async def test_update_reading_settings_partial_success(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test successful partial update of reading settings."""
        # Arrange
        current_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }
        
        update_data = ReadingSettingsUpdate(
            font_size="Large",
            color_mode="Dark"
        )

        expected_merged = {
            "font_size": "Large",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Dark",
        }

        mock_user_repo.get_reading_settings.return_value = current_settings
        mock_user_repo.update_reading_settings.return_value = MagicMock()

        # Act
        result = await update_reading_settings(update_data, mock_user_context, mock_db_session)

        # Assert
        assert isinstance(result, ReadingSettings)
        assert result.font_size == "Large"
        assert result.color_mode == "Dark"
        assert result.font_weight == "Normal"  # Unchanged
        
        # Verify repository calls
        mock_user_repo.get_reading_settings.assert_called_once_with(123)
        mock_user_repo.update_reading_settings.assert_called_once_with(123, expected_merged)

    async def test_update_reading_settings_fonts_only(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test updating only fonts in reading settings."""
        # Arrange
        current_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }
        
        update_data = ReadingSettingsUpdate(
            fonts={"headline": "Arial", "body": "Georgia", "caption": "Verdana"}
        )

        expected_merged = {
            "font_size": "Medium",
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }

        mock_user_repo.get_reading_settings.return_value = current_settings
        mock_user_repo.update_reading_settings.return_value = MagicMock()

        # Act
        result = await update_reading_settings(update_data, mock_user_context, mock_db_session)

        # Assert
        assert isinstance(result, ReadingSettings)
        assert result.fonts.headline == "Arial"
        assert result.fonts.body == "Georgia"
        assert result.font_size == "Medium"  # Unchanged
        
        mock_user_repo.update_reading_settings.assert_called_once_with(123, expected_merged)

    async def test_update_reading_settings_empty_update(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test updating reading settings with empty update (no changes)."""
        # Arrange
        current_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }
        
        update_data = ReadingSettingsUpdate()  # Empty update

        mock_user_repo.get_reading_settings.return_value = current_settings
        mock_user_repo.update_reading_settings.return_value = MagicMock()

        # Act
        result = await update_reading_settings(update_data, mock_user_context, mock_db_session)

        # Assert
        assert isinstance(result, ReadingSettings)
        assert result.font_size == "Medium"  # Unchanged
        assert result.color_mode == "Default"  # Unchanged
        
    async def test_get_reading_settings_user_not_found(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test get reading settings when user not found."""
        mock_user_repo.get_reading_settings.side_effect = UserNotFoundException("User not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_reading_settings(mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    async def test_get_reading_settings_database_error(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test get reading settings when database error occurs."""
        mock_user_repo.get_reading_settings.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_reading_settings(mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"

    async def test_create_reading_settings_user_not_found(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test create reading settings when user not found."""
        new_settings = ReadingSettings()
        mock_user_repo.update_reading_settings.side_effect = UserNotFoundException("User not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_reading_settings(new_settings, mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    async def test_create_reading_settings_database_error(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test create reading settings when database error occurs."""
        new_settings = ReadingSettings()
        mock_user_repo.update_reading_settings.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_reading_settings(new_settings, mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"
        mock_db_session.rollback.assert_called_once()

    async def test_update_reading_settings_user_not_found_on_get(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test update reading settings when user not found during get."""
        update_data = ReadingSettingsUpdate(font_size="Large")
        mock_user_repo.get_reading_settings.side_effect = UserNotFoundException("User not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_reading_settings(update_data, mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    async def test_update_reading_settings_user_not_found_on_update(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test update reading settings when user not found during update."""
        current_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }
        update_data = ReadingSettingsUpdate(font_size="Large")
        
        mock_user_repo.get_reading_settings.return_value = current_settings
        mock_user_repo.update_reading_settings.side_effect = UserNotFoundException("User not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_reading_settings(update_data, mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    async def test_update_reading_settings_database_error(self, mock_user_context, mock_db_session, mock_user_repo):
        """Test update reading settings when database error occurs."""
        current_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        }
        update_data = ReadingSettingsUpdate(font_size="Large")
        
        mock_user_repo.get_reading_settings.return_value = current_settings
        mock_user_repo.update_reading_settings.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_reading_settings(update_data, mock_user_context, mock_db_session)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"
        mock_db_session.rollback.assert_called_once()
