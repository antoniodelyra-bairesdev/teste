from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from ehp.base.jwt_helper import JWTGenerator
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.schema.password import PasswordResetConfirmSchema
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.services.password import confirm_password_reset
from ehp.utils import constants as const
from ehp.utils.authentication import check_password, hash_password


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_success():
    """Test successful password reset confirmation."""
    # Mock data for the user
    mock_auth = Authentication(
        id=123,
        user_name="mockuser",
        user_email="mock@example.com",
        user_pwd=hash_password("OldPa$sword123"),  # Current password
        is_active="1",
        is_confirmed="1",
        retry_count=0,
        reset_password=const.AUTH_RESET_PASSWORD,  # Reset password flag
        confirmation=None,  # No confirmation date needed for reset
        reset_token_expires=datetime.now() + timedelta(days=1),  # Valid reset token
    )

    # Mock AsyncSession
    mock_session = AsyncMock()
    
    # Mock AuthenticationRepository and its methods
    mock_repo = AsyncMock(spec=AuthenticationRepository)
    mock_repo.get_by_id = AsyncMock(return_value=mock_auth)
    mock_repo.update = AsyncMock()

    # Mock JWTGenerator and its decode_token method
    generator = JWTGenerator()
    jwt_generated = generator.generate(str(123), "mock@example.com", with_refresh=False)
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)

    # Create a mock PasswordResetConfirmSchema
    mock_params = PasswordResetConfirmSchema(
        token="valid_token",  # Token is mockable since we're testing logic
        new_password="NewPas$word123",
    )

    # Call the function under test with proper mocks
    with patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded):
        with patch("ehp.core.services.password.AuthenticationRepository", return_value=mock_repo):
            result = await confirm_password_reset(
                mock_params, session=mock_session
            )

    # Check that the password was updated and reset flags cleared
    mock_repo.get_by_id.assert_called_once_with(123)
    mock_repo.update.assert_called_once()
    
    # Verify that the auth object was modified correctly
    assert check_password(mock_auth.user_pwd, "NewPas$word123")
    assert mock_auth.reset_password == "0"
    assert mock_auth.reset_code is None
    
    # Check the response
    assert result.message == "Password has been reset successfully."
    assert result.code == 200


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_invalid_token():
    """Test password reset with invalid token."""
    mock_session = AsyncMock()
    
    mock_params = PasswordResetConfirmSchema(
        token="invalid_token",
        new_password="NewPas$word123"
    )

    # Mock JWTGenerator to raise ValueError for invalid token
    with patch("ehp.base.jwt_helper.JWTGenerator.decode_token", side_effect=ValueError("Invalid token")):
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(mock_params, session=mock_session)

    assert exc_info.value.status_code == 400
    assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_inactive_reset():
    """Test password reset when reset is not active."""
    mock_auth = Authentication(
        id=123,
        user_name="mockuser",
        user_email="test@example.com",
        user_pwd=hash_password("OldPassword123"),
        is_active="1",
        is_confirmed="1",
        retry_count=0,
        reset_password="0",  # Reset NOT active
        confirmation=None,
        reset_token_expires=datetime.now() + timedelta(days=1),  # Valid expiration
    )

    # Mock AsyncSession
    mock_session = AsyncMock()
    
    # Mock AuthenticationRepository
    mock_repo = AsyncMock(spec=AuthenticationRepository)
    mock_repo.get_by_id = AsyncMock(return_value=mock_auth)

    generator = JWTGenerator()
    jwt_generated = generator.generate(
        str(mock_auth.id), "test@example.com", with_refresh=False
    )
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)

    mock_params = PasswordResetConfirmSchema(
        token=jwt_generated.access_token, new_password="NewPas$word123"
    )

    # Call the function and expect an HTTPException for inactive reset
    with patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded):
        with patch("ehp.core.services.password.AuthenticationRepository", return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await confirm_password_reset(
                    mock_params, session=mock_session
                )

    # Check the correct error message based on the actual code
    assert exc_info.value.status_code == 400
    assert "Invalid token or reset request" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_expired_token():
    """Test password reset with expired reset token."""
    mock_auth = Authentication(
        id=123,
        user_name="mockuser",
        user_email="test@example.com",
        user_pwd=hash_password("OldPassword123"),
        is_active="1",
        is_confirmed="1",
        retry_count=0,
        reset_password=const.AUTH_RESET_PASSWORD,  # Reset active
        confirmation=None,
        reset_token_expires=datetime.now() - timedelta(days=1),  # EXPIRED token
    )

    # Mock AsyncSession
    mock_session = AsyncMock()
    
    # Mock AuthenticationRepository
    mock_repo = AsyncMock(spec=AuthenticationRepository)
    mock_repo.get_by_id = AsyncMock(return_value=mock_auth)

    generator = JWTGenerator()
    jwt_generated = generator.generate(
        str(mock_auth.id), "test@example.com", with_refresh=False
    )
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)

    mock_params = PasswordResetConfirmSchema(
        token=jwt_generated.access_token, new_password="NewPas$word123"
    )

    # Call the function and expect an HTTPException for expired token
    with patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded):
        with patch("ehp.core.services.password.AuthenticationRepository", return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await confirm_password_reset(
                    mock_params, session=mock_session
                )

    assert exc_info.value.status_code == 403
    assert "Reset token has expired or is not active" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
async def test_confirm_password_reset_user_not_found():
    """Test password reset when user is not found."""
    # Mock AsyncSession
    mock_session = AsyncMock()
    
    # Mock AuthenticationRepository to return None (user not found)
    mock_repo = AsyncMock(spec=AuthenticationRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    generator = JWTGenerator()
    jwt_generated = generator.generate(str(999), "nonexistent@example.com", with_refresh=False)
    decoded = generator.decode_token(jwt_generated.access_token, verify_exp=True)

    mock_params = PasswordResetConfirmSchema(
        token="valid_token",
        new_password="NewPas$word123"
    )

    with patch("ehp.base.jwt_helper.JWTGenerator.decode_token", return_value=decoded):
        with patch("ehp.core.services.password.AuthenticationRepository", return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await confirm_password_reset(
                    mock_params, session=mock_session
                )

    assert exc_info.value.status_code == 400
    assert "Invalid token or reset request" in exc_info.value.detail
