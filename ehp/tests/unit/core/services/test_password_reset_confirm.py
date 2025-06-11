import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from ehp.core.services.password_reset_confirm import confirm_password_reset
from ehp.core.models.schema.password import PasswordResetConfirmSchema
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.utils import hash_password, constants as const
from ehp.db.db_manager import DBManager
from ehp.base.jwt_helper import JWTGenerator


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_password_reset_success():
    """Test successful password reset confirmation."""
    # Create mock data for the user
    mock_auth = MagicMock()
    mock_auth.reset_password = const.AUTH_RESET_PASSWORD
    mock_auth.reset_code = "1234"
    mock_auth.user_pwd = hash_password("NewPassword123")

    # Mock the AuthenticationRepository and its methods
    mock_repo = MagicMock(AuthenticationRepository)
    mock_repo.get_by_id.return_value = mock_auth  # Correct method used here

    # Mock JWTGenerator and its decode_token method
    mock_jwt = MagicMock(JWTGenerator)
    mock_jwt.decode_token.return_value = {"sub": 1}  # Mock valid decoded token

    # Create a mock PasswordResetConfirmSchema
    mock_params = PasswordResetConfirmSchema(
        token="valid_token",  # Token is mockable since we're testing logic
        new_password="NewPassword123",
    )

    # Mock the session for database interaction
    mock_session = MagicMock(DBManager)

    # Call the function under test
    with patch("ehp.base.jwt_helper.JWTGenerator", return_value=mock_jwt):
        result = await confirm_password_reset(mock_params, session=mock_session)

    # Check that the password was updated and reset flags cleared
    assert mock_auth.user_pwd == hash_password("NewPassword123")
    assert mock_auth.reset_password == "0"
    assert mock_auth.reset_code is None
    mock_repo.update.assert_called_once()

    # Check if the result is the expected response
    assert result.message == "Password has been reset successfully."
    assert result.code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_password_reset_invalid_token():
    """Test password reset with an invalid or expired token."""
    mock_params = PasswordResetConfirmSchema(
        token="invalid_token", new_password="NewPassword123"  # Invalid token
    )

    # Simulating an invalid token case
    mock_repo = MagicMock(AuthenticationRepository)
    mock_repo.get_by_id.return_value = None  # No user found for token

    mock_jwt = MagicMock(JWTGenerator)
    mock_jwt.decode_token.side_effect = ValueError("Invalid token")

    mock_session = MagicMock(DBManager)

    # Call the function and expect an HTTPException to be raised
    with patch("ehp.base.jwt_helper.JWTGenerator", return_value=mock_jwt):
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(mock_params, session=mock_session)

    assert exc_info.value.status_code == 400
    assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_password_reset_inactive_reset():
    """Test password reset when reset is not active."""
    mock_auth = MagicMock()
    mock_auth.reset_password = "0"  # Reset not active
    mock_auth.reset_code = "1234"

    mock_repo = MagicMock(AuthenticationRepository)
    mock_repo.get_by_id.return_value = mock_auth

    mock_params = PasswordResetConfirmSchema(
        token="valid_token", new_password="NewPassword123"
    )

    mock_jwt = MagicMock(JWTGenerator)
    mock_jwt.decode_token.return_value = {"sub": 1}  # Mock valid decoded token

    mock_session = MagicMock(DBManager)

    # Call the function and expect an HTTPException for inactive reset
    with patch("ehp.base.jwt_helper.JWTGenerator", return_value=mock_jwt):
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(mock_params, session=mock_session)

    assert exc_info.value.status_code == 403
    assert "not active" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_password_reset_user_not_found():
    """Test when user is not found with the reset code."""
    mock_params = PasswordResetConfirmSchema(
        token="valid_token", new_password="NewPassword123"
    )

    mock_repo = MagicMock(AuthenticationRepository)
    mock_repo.get_by_id.return_value = None  # No user found

    mock_jwt = MagicMock(JWTGenerator)
    mock_jwt.decode_token.return_value = {"sub": 999}  # User ID not found

    mock_session = MagicMock(DBManager)

    # Call the function and expect an HTTPException (user not found)
    with patch("ehp.base.jwt_helper.JWTGenerator", return_value=mock_jwt):
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(mock_params, session=mock_session)

    assert exc_info.value.status_code == 400
    assert "Invalid token or reset request" in exc_info.value.detail
