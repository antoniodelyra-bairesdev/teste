from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from fastapi import HTTPException
from pydantic_core import ValidationError

from ehp.core.models.db import User
from ehp.core.models.schema.user import UserDisplayNameUpdateSchema
from ehp.core.services.session import AuthContext
from ehp.core.services.user import update_user_display_name
from ehp.db.db_manager import ManagedAsyncSession


@pytest.mark.unit
class TestUpdateUserDisplayName:
    """Unit tests for the update_user_display_name service function."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Provides a mock database session."""
        return AsyncMock(spec=ManagedAsyncSession)

    @pytest.fixture
    def sample_user(self) -> MagicMock:
        """Provides a sample user object for tests."""
        user = MagicMock(spec=User)
        user.id = 123
        user.display_name = "OldName"
        return user

    @pytest.fixture
    def mock_auth_context(self, sample_user: MagicMock) -> MagicMock:
        """Provides a mock authentication context using the sample user."""
        mock_auth = MagicMock(spec=AuthContext)
        mock_auth.user = sample_user
        return mock_auth

    @pytest.fixture
    def mock_user_repo(self) -> AsyncMock:
        """
        Provides a mock UserRepository instance and patches its import location.
        This single fixture replaces the repetitive @patch decorator in every test.
        """
        with patch("ehp.core.services.user.UserRepository", spec=True) as MockRepo:
            instance = MockRepo.return_value
            yield instance

    # Business Logic and Error Scenario Tests

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
