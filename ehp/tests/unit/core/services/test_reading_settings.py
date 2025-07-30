import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from ehp.core.models.schema.reading_settings import (
    ColorMode,
    FontOption,
    FontSettings,
    FontSize,
    FontWeight,
    LineSpacing,
    ReadingSettings,
    ReadingSettingsUpdate,
)
from ehp.core.repositories.user import UserNotFoundException, UserRepository
from ehp.core.services.reading_settings import (
    _create_validation_error_response,
    create_reading_settings,
    get_reading_settings,
    update_reading_settings,
)


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
        with patch(
            "ehp.core.services.reading_settings.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock(spec=UserRepository)
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    class TestValidationErrorHandling:
        """Test validation error handling and enum validation."""

        def test_create_validation_error_response_font_size(self):
            """Test validation error response for invalid font size."""
            # Create a ValidationError for font_size
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "enum",
                        "loc": ("font_size",),
                        "msg": "Input should be 'Small', 'Medium' or 'Large'",
                        "input": "ExtraLarge",
                        "ctx": {"expected": "'Small', 'Medium' or 'Large'"},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            assert (
                "Font size must be one of: Small, Medium, Large"
                in result.detail["errors"]
            )
            assert result.detail["message"] == "Reading settings validation failed"

        def test_create_validation_error_response_font_weight(self):
            """Test validation error response for invalid font weight."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "enum",
                        "loc": ("font_weight",),
                        "msg": "Input should be 'Light', 'Normal' or 'Bold'",
                        "input": "Medium",
                        "ctx": {"expected": "'Light', 'Normal' or 'Bold'"},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            assert (
                "Font weight must be one of: Light, Normal, Bold"
                in result.detail["errors"]
            )

        def test_create_validation_error_response_line_spacing(self):
            """Test validation error response for invalid line spacing."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "enum",
                        "loc": ("line_spacing",),
                        "msg": "Input should be 'Compact', 'Standard' or 'Spacious'",
                        "input": "Wide",
                        "ctx": {"expected": "'Compact', 'Standard' or 'Spacious'"},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            assert (
                "Line spacing must be one of: Compact, Standard, Spacious"
                in result.detail["errors"]
            )

        def test_create_validation_error_response_color_mode(self):
            """Test validation error response for invalid color mode."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "enum",
                        "loc": ("color_mode",),
                        "msg": "Input should be one of the allowed values",
                        "input": "Sepia",
                        "ctx": {
                            "expected": "Default, Dark, Red-Green Color Blindness, Blue-Yellow Color Blindness"
                        },
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            assert (
                "Color mode must be one of: Default, Dark, Red-Green Color Blindness, Blue-Yellow Color Blindness"
                in result.detail["errors"]
            )

        def test_create_validation_error_response_font_headline(self):
            """Test validation error response for invalid font headline."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "value_error",
                        "loc": ("fonts", "headline"),
                        "msg": "Font must be one of: System, Arial, Helvetica, Georgia, Times, Verdana, Courier",
                        "input": "Comic Sans",
                        "ctx": {"error": ValueError("Font must be one of: System, Arial, Helvetica, Georgia, Times, Verdana, Courier")},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            expected_msg = "Font must be one of: System, Arial, Helvetica, Georgia, Times, Verdana, Courier"
            assert expected_msg in result.detail["errors"]

        def test_create_validation_error_response_font_body(self):
            """Test validation error response for invalid font body."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "value_error",
                        "loc": ("fonts", "body"),
                        "msg": "Font must be one of: System, Arial, Helvetica, Georgia, Times, Verdana, Courier",
                        "input": "Wingdings",
                        "ctx": {"error": ValueError("Font must be one of: System, Arial, Helvetica, Georgia, Times, Verdana, Courier")},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            expected_msg = "Font must be one of: System, Arial, Helvetica, Georgia, Times, Verdana, Courier"
            assert expected_msg in result.detail["errors"]

        def test_create_validation_error_response_fonts_required(self):
            """Test validation error response for missing fonts."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "missing",
                        "loc": ("fonts",),
                        "msg": "Field required",
                        "input": {},
                        "ctx": {"error": ValueError("Field required")},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            # Aceitar a mensagem real retornada pelo handler
            assert "Invalid font setting: Field required" in result.detail["errors"]

        def test_create_validation_error_response_multiple_errors(self):
            """Test validation error response with multiple field errors."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "enum",
                        "loc": ("font_size",),
                        "msg": "Invalid font size",
                        "input": "ExtraLarge",
                        "ctx": {"expected": ", ".join([e.value for e in FontSize])},
                    },
                    {
                        "type": "enum",
                        "loc": ("color_mode",),
                        "msg": "Invalid color mode",
                        "input": "Sepia",
                        "ctx": {"expected": ", ".join([e.value for e in ColorMode])},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            assert len(result.detail["errors"]) == 2
            assert any("Font size must be one of" in error for error in result.detail["errors"])
            assert any("Color mode must be one of" in error for error in result.detail["errors"])

        def test_create_validation_error_response_unknown_field(self):
            """Test validation error response for unknown field."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError",
                [
                    {
                        "type": "value_error",
                        "loc": ("unknown_field",),
                        "msg": "Unknown field error",
                        "input": "invalid",
                        "ctx": {"error": ValueError("Unknown field error")},
                    }
                ],
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            # Aceitar a mensagem real retornada pelo handler
            assert "Invalid value for unknown_field: Value error, Unknown field error" in result.detail["errors"]

        def test_create_validation_error_response_empty_errors(self):
            """Test validation error response with empty errors list."""
            validation_error = ValidationError.from_exception_data(
                "ValidationError", []
            )

            result = _create_validation_error_response(validation_error)

            assert result.status_code == 422
            assert "Invalid reading settings format" in result.detail["errors"]

    class TestEnumValidation:
        """Test enum validation in schemas."""

        def test_font_size_enum_valid_values(self):
            """Test FontSize enum accepts valid values."""
            assert FontSize.SMALL == "Small"
            assert FontSize.MEDIUM == "Medium"
            assert FontSize.LARGE == "Large"

        def test_font_weight_enum_valid_values(self):
            """Test FontWeight enum accepts valid values."""
            assert FontWeight.LIGHT == "Light"
            assert FontWeight.NORMAL == "Normal"
            assert FontWeight.BOLD == "Bold"

        def test_line_spacing_enum_valid_values(self):
            """Test LineSpacing enum accepts valid values."""
            assert LineSpacing.COMPACT == "Compact"
            assert LineSpacing.STANDARD == "Standard"
            assert LineSpacing.SPACIOUS == "Spacious"

        def test_color_mode_enum_valid_values(self):
            """Test ColorMode enum accepts valid values."""
            assert ColorMode.DEFAULT == "Default"
            assert ColorMode.DARK == "Dark"
            assert ColorMode.RED_GREEN_COLORBLIND == "Red-Green Color Blindness"
            assert ColorMode.BLUE_YELLOW_COLORBLIND == "Blue-Yellow Color Blindness"

        def test_font_option_enum_valid_values(self):
            """Test FontOption enum accepts valid values."""
            assert FontOption.SYSTEM == "System"
            assert FontOption.ARIAL == "Arial"
            assert FontOption.HELVETICA == "Helvetica"
            assert FontOption.GEORGIA == "Georgia"
            assert FontOption.TIMES == "Times"
            assert FontOption.VERDANA == "Verdana"
            assert FontOption.COURIER == "Courier"

        def test_reading_settings_with_valid_enums(self):
            """Test ReadingSettings creation with valid enum values."""
            settings = ReadingSettings(
                font_size=FontSize.LARGE,
                font_weight=FontWeight.BOLD,
                line_spacing=LineSpacing.SPACIOUS,
                color_mode=ColorMode.DARK,
                fonts=FontSettings(headline="Arial", body="Georgia", caption="Verdana"),
            )

            assert settings.font_size == FontSize.LARGE
            assert settings.font_weight == FontWeight.BOLD
            assert settings.line_spacing == LineSpacing.SPACIOUS
            assert settings.color_mode == ColorMode.DARK

        def test_reading_settings_with_invalid_font_size(self):
            """Test ReadingSettings creation with invalid font size."""
            with pytest.raises(ValidationError) as exc_info:
                ReadingSettings(font_size="ExtraLarge")

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["type"] == "enum"
            assert "font_size" in str(errors[0]["loc"])

        def test_reading_settings_with_invalid_color_mode(self):
            """Test ReadingSettings creation with invalid color mode."""
            with pytest.raises(ValidationError) as exc_info:
                ReadingSettings(color_mode="Sepia")

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["type"] == "enum"
            assert "color_mode" in str(errors[0]["loc"])

        def test_reading_settings_with_invalid_fonts(self):
            """Test ReadingSettings creation with invalid font values."""
            with pytest.raises(ValidationError) as exc_info:
                ReadingSettings(
                    fonts=FontSettings(
                        headline="Comic Sans",  # Invalid font
                        body="System",
                        caption="System",
                    )
                )

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert "headline" in str(errors[0]["loc"])

        def test_reading_settings_update_with_invalid_values(self):
            """Test ReadingSettingsUpdate with invalid enum values."""
            with pytest.raises(ValidationError) as exc_info:
                ReadingSettingsUpdate(
                    font_size="ExtraLarge", font_weight="Medium", line_spacing="Wide"
                )

            errors = exc_info.value.errors()
            assert len(errors) == 3  # Three invalid enum values

        def test_font_settings_validation(self):
            """Test FontSettings validation with valid and invalid fonts."""
            # Valid fonts
            valid_fonts = FontSettings(
                headline="Arial", body="Georgia", caption="Verdana"
            )
            assert valid_fonts.headline == "Arial"
            assert valid_fonts.body == "Georgia"
            assert valid_fonts.caption == "Verdana"

            # Invalid fonts should raise ValidationError
            with pytest.raises(ValidationError):
                FontSettings(headline="Comic Sans", body="Wingdings", caption="Papyrus")

    class TestGetReadingSettings:
        """Test get reading settings functionality."""

        async def test_get_reading_settings_success(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test successful get reading settings."""
            # Arrange
            expected_settings = {
                "font_size": "Large",
                "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
                "font_weight": "Bold",
                "line_spacing": "Spacious",
                "color_mode": "Dark",
            }
            mock_user_repo.get_reading_settings.return_value = expected_settings

            # Act
            result = await get_reading_settings(mock_user_context, mock_db_session)

            # Assert
            assert isinstance(result, ReadingSettings)
            assert result.font_size == FontSize.LARGE
            assert result.fonts.headline == "Arial"
            assert result.color_mode == ColorMode.DARK
            mock_user_repo.get_reading_settings.assert_called_once_with(123)

        async def test_get_reading_settings_with_defaults(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
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
            assert result.font_size == FontSize.MEDIUM
            assert result.fonts.headline == "System"
            assert result.color_mode == ColorMode.DEFAULT

        async def test_get_reading_settings_validation_error(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test get reading settings handles validation errors."""
            # Arrange - repository returns invalid data
            invalid_settings = {
                "font_size": "ExtraLarge",  # Invalid enum value
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }
            mock_user_repo.get_reading_settings.return_value = invalid_settings

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_reading_settings(mock_user_context, mock_db_session)

            assert exc_info.value.status_code == 422
            assert "Font size must be one of" in str(exc_info.value.detail["errors"])

        async def test_get_reading_settings_user_not_found(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test get reading settings when user not found."""
            mock_user_repo.get_reading_settings.side_effect = UserNotFoundException(
                "User not found"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_reading_settings(mock_user_context, mock_db_session)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "User not found"

        async def test_get_reading_settings_database_error(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test get reading settings when database error occurs."""
            mock_user_repo.get_reading_settings.side_effect = Exception(
                "Database error"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_reading_settings(mock_user_context, mock_db_session)

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Internal server error"

    class TestCreateReadingSettings:
        """Test create reading settings functionality."""

        async def test_create_reading_settings_success(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test successful create reading settings."""
            # Arrange
            new_settings = ReadingSettings(
                font_size=FontSize.SMALL,
                fonts=FontSettings(headline="Times", body="Helvetica", caption="Arial"),
                font_weight=FontWeight.LIGHT,
                line_spacing=LineSpacing.COMPACT,
                color_mode=ColorMode.RED_GREEN_COLORBLIND,
            )
            mock_user_repo.update_reading_settings.return_value = MagicMock()

            # Act
            result = await create_reading_settings(
                new_settings, mock_user_context, mock_db_session
            )

            # Assert
            assert isinstance(result, ReadingSettings)
            assert result.font_size == FontSize.SMALL
            assert result.fonts.headline == "Times"
            assert result.color_mode == ColorMode.RED_GREEN_COLORBLIND
            mock_user_repo.update_reading_settings.assert_called_once_with(
                123, new_settings.model_dump()
            )

        async def test_create_reading_settings_user_not_found(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test create reading settings when user not found."""
            new_settings = ReadingSettings()
            mock_user_repo.update_reading_settings.side_effect = UserNotFoundException(
                "User not found"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await create_reading_settings(
                    new_settings, mock_user_context, mock_db_session
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "User not found"

        async def test_create_reading_settings_database_error(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test create reading settings when database error occurs."""
            new_settings = ReadingSettings()
            mock_user_repo.update_reading_settings.side_effect = Exception(
                "Database error"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await create_reading_settings(
                    new_settings, mock_user_context, mock_db_session
                )

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Internal server error"
            mock_db_session.rollback.assert_called_once()

    class TestUpdateReadingSettings:
        """Test update reading settings functionality."""

        async def test_update_reading_settings_partial_success(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
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
                font_size=FontSize.LARGE, color_mode=ColorMode.DARK
            )

            mock_user_repo.get_reading_settings.return_value = current_settings
            mock_user_repo.update_reading_settings.return_value = MagicMock()

            # Act
            result = await update_reading_settings(
                update_data, mock_user_context, mock_db_session
            )

            # Assert
            assert isinstance(result, ReadingSettings)
            assert result.font_size == FontSize.LARGE
            assert result.color_mode == ColorMode.DARK
            assert result.font_weight == FontWeight.NORMAL  # Unchanged

            # Verify repository calls
            mock_user_repo.get_reading_settings.assert_called_once_with(123)
            mock_user_repo.update_reading_settings.assert_called_once()

        async def test_update_reading_settings_with_invalid_merge(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test update reading settings when merge results in invalid data."""
            # Arrange
            current_settings = {
                "font_size": "ExtraLarge",  # Invalid value in current settings
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }

            update_data = ReadingSettingsUpdate(color_mode=ColorMode.DARK)

            mock_user_repo.get_reading_settings.return_value = current_settings
            mock_user_repo.update_reading_settings.return_value = MagicMock()

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await update_reading_settings(
                    update_data, mock_user_context, mock_db_session
                )

            assert exc_info.value.status_code == 422
            assert "Font size must be one of" in str(exc_info.value.detail["errors"])

        async def test_update_reading_settings_fonts_only(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
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
                fonts=FontSettings(headline="Arial", body="Georgia", caption="Verdana")
            )

            mock_user_repo.get_reading_settings.return_value = current_settings
            mock_user_repo.update_reading_settings.return_value = MagicMock()

            # Act
            result = await update_reading_settings(
                update_data, mock_user_context, mock_db_session
            )

            # Assert
            assert isinstance(result, ReadingSettings)
            assert result.fonts.headline == "Arial"
            assert result.fonts.body == "Georgia"
            assert result.font_size == FontSize.MEDIUM  # Unchanged

            mock_user_repo.update_reading_settings.assert_called_once()

        async def test_update_reading_settings_empty_update(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
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
            result = await update_reading_settings(
                update_data, mock_user_context, mock_db_session
            )

            # Assert
            assert isinstance(result, ReadingSettings)
            assert result.font_size == FontSize.MEDIUM  # Unchanged
            assert result.color_mode == ColorMode.DEFAULT  # Unchanged

        async def test_update_reading_settings_user_not_found_on_get(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test update reading settings when user not found during get."""
            update_data = ReadingSettingsUpdate(font_size=FontSize.LARGE)
            mock_user_repo.get_reading_settings.side_effect = UserNotFoundException(
                "User not found"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await update_reading_settings(
                    update_data, mock_user_context, mock_db_session
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "User not found"

        async def test_update_reading_settings_user_not_found_on_update(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test update reading settings when user not found during update."""
            current_settings = {
                "font_size": "Medium",
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }
            update_data = ReadingSettingsUpdate(font_size=FontSize.LARGE)

            mock_user_repo.get_reading_settings.return_value = current_settings
            mock_user_repo.update_reading_settings.side_effect = UserNotFoundException(
                "User not found"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await update_reading_settings(
                    update_data, mock_user_context, mock_db_session
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "User not found"

        async def test_update_reading_settings_database_error(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test update reading settings when database error occurs."""
            current_settings = {
                "font_size": "Medium",
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }
            update_data = ReadingSettingsUpdate(font_size=FontSize.LARGE)

            mock_user_repo.get_reading_settings.return_value = current_settings
            mock_user_repo.update_reading_settings.side_effect = Exception(
                "Database error"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await update_reading_settings(
                    update_data, mock_user_context, mock_db_session
                )

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Internal server error"
            mock_db_session.rollback.assert_called_once()

        async def test_update_reading_settings_with_invalid_fonts_in_update(
            self, mock_user_context, mock_db_session, mock_user_repo
        ):
            """Test update reading settings with invalid fonts in update data."""
            # Arrange
            current_settings = {
                "font_size": "Medium",
                "fonts": {"headline": "System", "body": "System", "caption": "System"},
                "font_weight": "Normal",
                "line_spacing": "Standard",
                "color_mode": "Default",
            }

            # This should raise ValidationError when creating FontSettings
            with pytest.raises(ValidationError):
                update_data = ReadingSettingsUpdate(
                    fonts=FontSettings(
                        headline="Comic Sans", body="System", caption="System"
                    )
                )
