from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from pydantic_core import ValidationError
from sqlalchemy.exc import IntegrityError
from PIL import Image

from ehp.core.models.db import User
from ehp.core.models.schema.user import (
    UserDisplayNameUpdateSchema,
    UserProfileUpdateSchema, 
    EmailChangeRequestSchema,
    UpdatePasswordSchema,
    UpdateUserSettings,
    UserCategoriesUpdateSchema,
    PasswordChangeSchema
)
from ehp.core.services.session import AuthContext
from ehp.core.services.user import (
    update_user_display_name,
    update_user_profile,
    request_email_change,
    confirm_email_change,
    update_password_by_id,
    update_user_settings,
    upload_avatar,
    update_user_categories,
    generate_email_change_token,
    change_password
)
from ehp.db.db_manager import ManagedAsyncSession


# ============================================================================
# SHARED FIXTURES - Used across multiple test classes
# ============================================================================

@pytest.fixture
def mock_session() -> AsyncMock:
    """Provides a mock database session."""
    return AsyncMock(spec=ManagedAsyncSession)


@pytest.fixture
def sample_user() -> MagicMock:
    """Provides a sample user object for tests."""
    user = MagicMock(spec=User)
    user.id = 123
    user.display_name = "OldName"
    user.full_name = "John Doe"
    user.email_notifications = True
    user.readability_preferences = {}
    return user


@pytest.fixture
def mock_auth_context(sample_user: MagicMock) -> MagicMock:
    """Provides a mock authentication context using the sample user."""
    mock_auth = MagicMock(spec=AuthContext)
    mock_auth.user = sample_user
    mock_auth.user.auth_id = 456
    mock_auth.user_email = "current@example.com"
    mock_auth.id = 123
    mock_auth.email_change_token_expires = datetime.now() + timedelta(hours=1)
    mock_auth.pending_email = "new@example.com"
    return mock_auth


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Provides a mock UserRepository instance."""
    with patch("ehp.core.services.user.UserRepository", spec=True) as MockRepo:
        instance = MockRepo.return_value
        yield instance


@pytest.fixture
def mock_auth_repo() -> AsyncMock:
    """Provides a mock AuthenticationRepository instance."""
    with patch("ehp.core.services.user.AuthenticationRepository", spec=True) as MockRepo:
        instance = MockRepo.return_value
        yield instance


@pytest.fixture
def mock_upload_file() -> MagicMock:
    """Provides a mock UploadFile."""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    
    # Create a small valid JPEG image content
    img = Image.new('RGB', (10, 10), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    mock_file.read = AsyncMock(return_value=img_bytes.getvalue())
    return mock_file


@pytest.mark.unit
class TestUpdateUserDisplayName:
    """Unit tests for the update_user_display_name service function."""

    async def test_user_not_found(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """
        Test that a 404 HTTPException is raised if the user is not found in the database.
        This covers the log and exception lines for a non-existent user.
        """
        # Arrange
        mock_user_repo.get_by_id.return_value = None
        display_name_data = UserDisplayNameUpdateSchema(display_name="any_name")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"
        mock_user_repo.get_by_id.assert_called_once_with(mock_auth_context.user.id)

    async def test_display_name_conflict(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test that a 409 HTTPException is raised if the display name is already taken."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = True  # Simulate name conflict
        display_name_data = UserDisplayNameUpdateSchema(display_name="ExistingName")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "This display name is already taken"
        mock_user_repo.update.assert_not_called()

    async def test_validation_error_on_model_assignment(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """
        Ensures a ValidationError raised during attribute assignment (e.g., by a
        DB model validator) is caught and handled correctly.
        """
        # Arrange
        # Set up for a successful path until the model attribute assignment
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = False

        # Create the validation error to be raised
        # The fix is to provide the actual error instance in the 'ctx' dictionary.
        error_message = "Invalid value set on model"
        validation_error = ValidationError.from_exception_data(
            "ModelValidationError",
            [
                {
                    "type": "value_error",
                    "loc": ("display_name",),
                    "msg": error_message,
                    "input": "NewInvalidName",
                    "ctx": {"error": ValueError(error_message)},
                }
            ],
        )

        # Mock the 'display_name' property on the sample_user object.
        # When `user.display_name = "..."` is called, it will raise the error.
        type(sample_user).display_name = PropertyMock(side_effect=validation_error)
        display_name_data = UserDisplayNameUpdateSchema(display_name="NewInvalidName")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == f"Value error, {error_message}"
        mock_user_repo.update.assert_not_called()

    @pytest.mark.parametrize(
        "raised_exception, expected_status, expected_detail",
        [
            pytest.param(
                Exception("Database connection failed"),
                500,
                "Internal server error",
                id="generic_exception_maps_to_500",
            ),
            pytest.param(
                HTTPException(status_code=400, detail="Custom repo error"),
                400,
                "Custom repo error",
                id="http_exception_is_re-raised",
            ),
            pytest.param(
                ValidationError.from_exception_data(
                    "SchemaError",
                    [
                        {
                            "type": "string_too_short",
                            "loc": ("display_name",),
                            "msg": "String should have at least 2 characters",
                            "input": "a",
                            "ctx": {"min_length": 2},
                        }
                    ],
                ),
                422,
                "String should have at least 2 characters",
                id="validation_error_with_details_maps_to_422",
            ),
            pytest.param(
                ValidationError.from_exception_data("SchemaError", []),
                422,
                "Invalid display name format",
                id="validation_error_empty_errors_maps_to_422_with_default_msg",
            ),
        ],
    )
    async def test_exception_handling_during_repo_update(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
        raised_exception: Exception,
        expected_status: int,
        expected_detail: str,
    ):
        """
        Test that various exceptions raised during the repository `update` call
        are caught and mapped to the correct HTTPExceptions. This covers the
        entire `try...except` block for failures at the final stage.
        """
        # Arrange: Setup for a valid update attempt that will fail at the `update` call.
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = False
        mock_user_repo.update.side_effect = raised_exception
        display_name_data = UserDisplayNameUpdateSchema(display_name="NewValidName")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == expected_status
        assert exc_info.value.detail == expected_detail

    # Success Scenario Tests

    async def test_update_display_name_success(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test a successful display name update on the happy path."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = False
        display_name_data = UserDisplayNameUpdateSchema(display_name="NewDisplayName")

        # Act
        result = await update_user_display_name(
            display_name_data, mock_session, mock_auth_context
        )

        # Assert
        mock_user_repo.update.assert_called_once()
        assert result.display_name == "NewDisplayName"
        assert result.message == "Display name updated successfully"
        assert sample_user.display_name == "NewDisplayName"

    async def test_update_display_name_unchanged(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test that providing the same display name results in no database update."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        display_name_data = UserDisplayNameUpdateSchema(display_name="OldName")

        # Act
        result = await update_user_display_name(
            display_name_data, mock_session, mock_auth_context
        )

        # Assert
        mock_user_repo.display_name_exists.assert_not_called()
        mock_user_repo.update.assert_not_called()
        assert result.display_name == "OldName"
        assert result.message == "Display name unchanged (same value provided)"

    async def test_update_display_name_case_sensitivity(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test case sensitivity behavior - system should be case-insensitive."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        # Simulate that a user with "testuser" already exists (case-insensitive check)
        mock_user_repo.display_name_exists.return_value = True
        display_name_data = UserDisplayNameUpdateSchema(display_name="TestUser")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )

        # Should return 409 Conflict because "TestUser" conflicts with existing "testuser"
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "This display name is already taken"
        mock_user_repo.display_name_exists.assert_called_once_with(
            "TestUser", exclude_user_id=123
        )
        mock_user_repo.update.assert_not_called()

    async def test_integrity_error_unique_constraint(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test IntegrityError with unique constraint is handled as 409 conflict."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = False
        integrity_error = IntegrityError("unique constraint violated", None, None)
        mock_user_repo.update.side_effect = integrity_error
        display_name_data = UserDisplayNameUpdateSchema(display_name="ConflictName")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "This display name is already taken"

    async def test_integrity_error_duplicate_key(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test IntegrityError with duplicate key is handled as 409 conflict."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = False
        integrity_error = IntegrityError("duplicate key value", None, None)
        mock_user_repo.update.side_effect = integrity_error
        display_name_data = UserDisplayNameUpdateSchema(display_name="ConflictName")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "This display name is already taken"

    async def test_integrity_error_other(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        sample_user: MagicMock,
    ):
        """Test other IntegrityError is handled as 500 error."""
        # Arrange
        mock_user_repo.get_by_id.return_value = sample_user
        mock_user_repo.display_name_exists.return_value = False
        integrity_error = IntegrityError("some other constraint", None, None)
        mock_user_repo.update.side_effect = integrity_error
        display_name_data = UserDisplayNameUpdateSchema(display_name="ValidName")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_display_name(
                display_name_data, mock_session, mock_auth_context
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Database integrity error"


@pytest.mark.unit 
class TestUpdateUserProfile:
    """Unit tests for the update_user_profile service function."""

    async def test_update_user_profile_user_not_found(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test UserNotFoundException is handled correctly."""
        from ehp.core.repositories.user import UserNotFoundException
        
        # Arrange
        mock_user_repo.update_full_name.side_effect = UserNotFoundException()
        profile_data = UserProfileUpdateSchema(full_name="New Name")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_profile(profile_data, mock_session, mock_auth_context)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"
        mock_session.rollback.assert_called_once()

    async def test_update_user_profile_http_exception(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test HTTPException is re-raised correctly."""
        # Arrange
        http_exception = HTTPException(status_code=400, detail="Bad request")
        mock_user_repo.update_full_name.side_effect = http_exception
        profile_data = UserProfileUpdateSchema(full_name="New Name")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_profile(profile_data, mock_session, mock_auth_context)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Bad request"
        mock_session.rollback.assert_called_once()

    async def test_update_user_profile_generic_exception(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test generic Exception is handled as 500 error."""
        # Arrange
        mock_user_repo.update_full_name.side_effect = Exception("Database error")
        profile_data = UserProfileUpdateSchema(full_name="New Name")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_profile(profile_data, mock_session, mock_auth_context)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestUpdatePasswordById:
    """Unit tests for the update_password_by_id service function."""

    async def test_update_password_user_not_found(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
    ):
        """Test user not found case (line 373)."""
        # Arrange
        mock_auth_repo.get_by_id.return_value = None
        payload = UpdatePasswordSchema(
            new_password="NewPassword123!",
            reset_token="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            logout=False
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_password_by_id(123, payload, mock_session)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found."

    @patch("ehp.core.services.user.SessionManager")
    @patch("ehp.core.services.user.timezone_now")
    async def test_update_password_with_logout(
        self,
        mock_timezone_now: MagicMock,
        mock_session_manager_class: MagicMock,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
    ):
        """Test logout functionality (lines 398-401)."""
        # Arrange
        reset_token = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        mock_user = MagicMock()
        mock_user.reset_token = reset_token
        
        # Mock timezone_now to return a timezone-aware datetime
        from ehp.utils.date_utils import timezone_now
        current_time = timezone_now()
        mock_timezone_now.return_value = current_time
        mock_user.reset_token_expires = current_time + timedelta(hours=1)
        
        mock_user.user_pwd = "hashed_old_password"
        mock_user.id = 123
        mock_auth_repo.get_by_id.return_value = mock_user
        
        mock_session_manager = MagicMock()
        mock_session_manager_class.return_value = mock_session_manager

        payload = UpdatePasswordSchema(
            new_password="NewPassword123!",
            reset_token="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            logout=True
        )

        with patch("ehp.core.services.user.check_password", return_value=False), \
             patch("ehp.core.services.user.hash_password", return_value="new_hashed_password"):

            # Act
            await update_password_by_id(123, payload, mock_session)

            # Assert
            mock_session_manager.wipe_sessions.assert_called_once_with("123")


@pytest.mark.unit
class TestRequestEmailChange:
    """Unit tests for the request_email_change service function."""

    async def test_request_email_change_auth_not_found(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test authentication record not found (line 449)."""
        # Arrange
        mock_auth_repo.get_by_email.return_value = None  # No existing user with new email
        mock_auth_repo.get_by_id.return_value = None  # Auth record not found
        request_data = EmailChangeRequestSchema(new_email="new@example.com")

        with patch("ehp.core.services.user.SessionManager"):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await request_email_change(request_data, mock_session, mock_auth_context)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "User authentication not found"

    @patch("ehp.core.services.user.send_notification")
    async def test_request_email_change_exception_handling(
        self,
        mock_send_notification: MagicMock,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test exception handling (lines 496-498)."""
        # Arrange
        mock_auth_repo.get_by_email.return_value = None
        mock_auth_repo.get_by_id.side_effect = Exception("Database error")
        request_data = EmailChangeRequestSchema(new_email="new@example.com")

        with patch("ehp.core.services.user.SessionManager"):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await request_email_change(request_data, mock_session, mock_auth_context)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Internal server error"


@pytest.mark.unit
class TestConfirmEmailChange:
    """Unit tests for the confirm_email_change service function."""

    @patch("ehp.core.services.user.send_notification")
    async def test_confirm_email_change_notification_exception(
        self,
        mock_send_notification: MagicMock,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test exception in sending confirmation email (lines 559-561)."""
        # Arrange
        mock_send_notification.side_effect = Exception("Email service error")

        # Act
        result = await confirm_email_change(mock_auth_context, mock_session)

        # Assert - should still succeed despite email failure
        assert result.message == "Email address updated successfully"
        assert result.code == 200

    async def test_confirm_email_change_exception_handling(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test exception handling (lines 570-572)."""
        # Arrange
        mock_auth_repo.update.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await confirm_email_change(mock_auth_context, mock_session)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"


@pytest.mark.unit
class TestUploadAvatar:
    """Unit tests for the upload_avatar service function."""

    async def test_upload_avatar_invalid_image_format(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test invalid image format exception (line 630)."""
        # Arrange
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.jpg" 
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"invalid image data")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(mock_session, mock_auth_context, mock_file)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid image file"

    async def test_upload_avatar_user_not_found(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
        mock_upload_file: MagicMock,
    ):
        """Test UserNotFoundException (line 665)."""
        from ehp.core.repositories.user import UserNotFoundException
        
        # Arrange
        mock_user_repo.update_avatar.side_effect = UserNotFoundException()

        with patch("ehp.core.services.user.AWSClient"), \
             patch("ehp.core.services.user.settings") as mock_settings:
            mock_settings.MAX_FILE_SIZE = 1024000
            mock_settings.AWS_S3_BUCKET = "test-bucket"
            mock_settings.AWS_REGION_NAME = "us-east-1"

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await upload_avatar(mock_session, mock_auth_context, mock_upload_file)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "User not found"


@pytest.mark.unit
class TestUpdateUserCategories:
    """Unit tests for the update_user_categories service function."""

    async def test_update_user_categories_exception_handling(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test exception handling (lines 707-708)."""
        # Arrange
        mock_user_repo.update_preferred_news_categories.side_effect = Exception("Database error")
        categories_data = UserCategoriesUpdateSchema(category_ids=[1, 2, 3])

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_user_categories(categories_data, mock_session, mock_auth_context)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestGenerateEmailChangeToken:
    """Unit tests for the generate_email_change_token function."""

    def test_generate_email_change_token(self):
        """Test token generation returns a 64-character hex string."""
        # Act
        token = generate_email_change_token()

        # Assert
        assert isinstance(token, str)
        assert len(token) == 64
        assert all(c in '0123456789abcdef' for c in token)


@pytest.mark.unit
class TestChangePassword:
    """Unit tests for the change_password service function."""

    async def test_change_password_auth_not_found(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test authentication record not found (lines 306-311)."""
        # Arrange
        mock_auth_repo.get_by_id.return_value = None
        password_data = PasswordChangeSchema(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await change_password(password_data, mock_session, mock_auth_context)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User authentication not found"

    async def test_change_password_incorrect_current_password(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test incorrect current password (lines 314-318)."""
        # Arrange
        mock_auth = MagicMock()
        mock_auth.user_pwd = "hashed_password"
        mock_auth_repo.get_by_id.return_value = mock_auth
        
        password_data = PasswordChangeSchema(
            current_password="WrongPassword123!",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )

        with patch("ehp.core.services.user.check_password", return_value=False):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await change_password(password_data, mock_session, mock_auth_context)
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "Current password is incorrect"

    async def test_change_password_update_failed(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test password update failure (lines 326-331)."""
        # Arrange
        mock_auth = MagicMock()
        mock_auth.user_pwd = "hashed_password"
        mock_auth.id = 456
        mock_auth_repo.get_by_id.return_value = mock_auth
        mock_auth_repo.update_password.return_value = False  # Update failed
        
        password_data = PasswordChangeSchema(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )

        with patch("ehp.core.services.user.check_password", return_value=True), \
             patch("ehp.core.services.user.hash_password", return_value="new_hashed_password"):
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await change_password(password_data, mock_session, mock_auth_context)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to update password"

    async def test_change_password_generic_exception(
        self,
        mock_auth_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test generic exception handling (lines 340-345)."""
        # Arrange
        mock_auth_repo.get_by_id.side_effect = Exception("Database error")
        password_data = PasswordChangeSchema(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await change_password(password_data, mock_session, mock_auth_context)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestUpdateUserSettings:
    """Unit tests for the update_user_settings service function."""

    async def test_update_user_settings_email_notifications(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test updating email notifications setting (lines 587-588)."""
        # Arrange
        payload = UpdateUserSettings(email_notifications=False)

        # Act
        await update_user_settings(mock_auth_context, mock_session, payload)

        # Assert
        assert mock_auth_context.user.email_notifications == False
        mock_user_repo.update.assert_called_once_with(mock_auth_context.user)

    async def test_update_user_settings_readability_preferences(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test updating readability preferences setting (lines 589-590)."""
        # Arrange
        new_prefs = {"font_size": "large", "theme": "dark"}
        payload = UpdateUserSettings(readability_preferences=new_prefs)

        # Act
        await update_user_settings(mock_auth_context, mock_session, payload)

        # Assert
        assert mock_auth_context.user.readability_preferences == new_prefs
        mock_user_repo.update.assert_called_once_with(mock_auth_context.user)

    async def test_update_user_settings_both_settings(
        self,
        mock_user_repo: AsyncMock,
        mock_session: AsyncMock,
        mock_auth_context: MagicMock,
    ):
        """Test updating both settings (lines 587-591)."""
        # Arrange
        new_prefs = {"font_size": "medium"}
        payload = UpdateUserSettings(
            email_notifications=False,
            readability_preferences=new_prefs
        )

        # Act
        await update_user_settings(mock_auth_context, mock_session, payload)

        # Assert
        assert mock_auth_context.user.email_notifications == False
        assert mock_auth_context.user.readability_preferences == new_prefs
        mock_user_repo.update.assert_called_once_with(mock_auth_context.user)
