from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from ehp.base.jwt_helper import JWTGenerator
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.schema.password import PasswordResetConfirmSchema
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.services.password import confirm_password_reset
from ehp.db.db_manager import DBManager
from ehp.utils import constants as const
from ehp.utils import hash_password
from ehp.utils.authentication import check_password


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_success(test_db_manager: DBManager):
    """Test successful password reset confirmation."""
    # Create mock data for the user
    mock_auth = Authentication(
        id=123,
        user_name="mockuser",
        user_email="mock@example.com",
        user_pwd=hash_password("NewPassword123"),
        is_active="1",
        is_confirmed="1",
        retry_count=0,
        reset_password=const.AUTH_RESET_PASSWORD,  # Reset password flag
        confirmation=None,  # No confirmation date needed for reset
        reset_token_expires=datetime.now() + timedelta(days=1),  # Valid reset token
    )
    repository = AuthenticationRepository(test_db_manager.get_session(), Authentication)
    await repository.create(mock_auth)

    # Mock JWTGenerator and its decode_token method
    generator = JWTGenerator()
    jwt_generated = generator.generate(str(1), "test@example.com", with_refresh=False)
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)

    # Create a mock PasswordResetConfirmSchema
    mock_params = PasswordResetConfirmSchema(
        token="valid_token",  # Token is mockable since we're testing logic
        new_password="NewPassword123",
    )

    # Call the function under test
    with (
        patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded),
        patch(
            "ehp.core.repositories.AuthenticationRepository.get_by_id",
            return_value=mock_auth,
        ),
    ):
        result = await confirm_password_reset(
            mock_params, session=test_db_manager.get_session()
        )

    # Check that the password was updated and reset flags cleared
    assert check_password(mock_auth.user_pwd, "NewPassword123")
    assert mock_auth.reset_password == "0"
    assert mock_auth.reset_code is None

    # Check if the result is the expected response
    assert result.message == "Password has been reset successfully."
    assert result.code == 200


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_invalid_token():
    """Test password reset with an invalid or expired token."""
    mock_params = PasswordResetConfirmSchema(
        token="invalid_token",
        new_password="NewPassword123",  # Invalid token
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
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_inactive_reset(test_db_manager: DBManager):
    """Test password reset when reset is not active."""
    mock_auth = Authentication(
        id=123,
        user_name="mockuser",
        user_email="test@example.com",
        user_pwd=hash_password("NewPassword123"),
        is_active="1",
        is_confirmed="1",
        retry_count=0,
        reset_password=const.AUTH_RESET_PASSWORD,  # Reset password flag
        confirmation=None,  # No confirmation date needed for reset
        reset_token_expires=datetime.now()
        - timedelta(days=1),  # Simulate an expired reset token
    )
    repository = AuthenticationRepository(test_db_manager.get_session(), Authentication)
    await repository.create(mock_auth)

    mock_repo = MagicMock(AuthenticationRepository)
    mock_repo.get_by_id.return_value = mock_auth

    generator = JWTGenerator()
    jwt_generated = generator.generate(
        str(mock_auth.id), "test@example.com", with_refresh=False
    )
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)

    mock_params = PasswordResetConfirmSchema(
        token=jwt_generated.access_token, new_password="NewPassword123"
    )

    # Call the function and expect an HTTPException for inactive reset
    with patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded):
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(
                mock_params, session=test_db_manager.get_session()
            )

    assert "not active" in exc_info.value.detail
    assert exc_info.value.status_code == 403


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_user_not_found():
    """Test when user is not found with the reset code."""
    mock_params = PasswordResetConfirmSchema(
        token="valid_token", new_password="NewPassword123"
    )

    generator = JWTGenerator()
    jwt_generated = generator.generate(str(999), "test@example.com", with_refresh=False)
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)
    mock_repo = MagicMock(spec=AuthenticationRepository)
    mock_repo.get_by_id.return_value = None  # No user found

    mock_session = MagicMock(DBManager)

    # Call the function and expect an HTTPException (user not found)
    with (
        patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded),
        patch("ehp.core.services.password.AuthenticationRepository", return_value=mock_repo),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(mock_params, session=mock_session)

    assert exc_info.value.status_code == 400
    assert "Invalid token or reset request" in exc_info.value.detail
