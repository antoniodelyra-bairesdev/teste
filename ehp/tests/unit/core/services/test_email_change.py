from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi import HTTPException
import pytest
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.schema.user import EmailChangeRequestSchema
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.services.user import (
    confirm_email_change,
    generate_email_change_token,
    request_email_change,
)
from ehp.utils.authentication import hash_password


@pytest.mark.unit
class TestEmailChangeService:
    """Unit tests for email change functionality."""

    @pytest.fixture
    def mock_auth_user(self):
        """Create a mock authenticated user."""
        auth = Authentication(
            id=123,
            user_name="testuser",
            user_email="test@example.com",
            user_pwd=hash_password("TestPass123"),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
        )
        return auth

    @pytest.fixture
    def mock_auth_context(self, mock_auth_user):
        """Create a mock AuthContext."""
        mock_context = MagicMock()
        mock_context.id = mock_auth_user.id
        mock_context.user_email = mock_auth_user.user_email
        mock_context.user = MagicMock()
        return mock_context

    def test_generate_email_change_token(self):
        """Test that email change token generation works."""
        token = generate_email_change_token()

        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes hex = 64 characters

        # Generate another token to ensure they're different
        token2 = generate_email_change_token()
        assert token != token2

    async def test_request_email_change_success(
        self,
        mock_auth_context,
        mock_auth_user,
        mock_redis,
    ):
        """Test successful email change request."""
        mock_session = AsyncMock()
        mock_repo = AsyncMock(spec=AuthenticationRepository)
        mock_repo.get_by_email.return_value = None  # New email not in use
        mock_repo.get_by_id.return_value = mock_auth_user
        mock_repo.update.return_value = None

        request_data = EmailChangeRequestSchema(new_email="newemail@example.com")

        with patch(
            "ehp.core.services.user.AuthenticationRepository", return_value=mock_repo
        ):
            with patch("ehp.core.services.user.send_notification", return_value=True):
                result = await request_email_change(
                    request_data, mock_session, mock_auth_context
                )

        assert result.message == "Verification email sent to your new email address"
        assert result.code == 200
        mock_repo.get_by_email.assert_called_once_with("newemail@example.com")
        mock_repo.update.assert_called_once()

    async def test_request_email_change_same_email(self, mock_auth_context):
        """Test email change request with same email."""
        mock_session = AsyncMock()
        request_data = EmailChangeRequestSchema(new_email="test@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await request_email_change(request_data, mock_session, mock_auth_context)

        assert exc_info.value.status_code == 400
        assert "must be different" in exc_info.value.detail

    async def test_request_email_change_email_in_use(
        self, mock_auth_context, mock_auth_user
    ):
        """Test email change request with email already in use."""
        mock_session = AsyncMock()
        mock_repo = AsyncMock(spec=AuthenticationRepository)

        # Email already in use by different user
        existing_user = Authentication(id=456, user_email="newemail@example.com")
        mock_repo.get_by_email.return_value = existing_user

        request_data = EmailChangeRequestSchema(new_email="newemail@example.com")

        with patch(
            "ehp.core.services.user.AuthenticationRepository", return_value=mock_repo
        ):
            with pytest.raises(HTTPException) as exc_info:
                await request_email_change(
                    request_data, mock_session, mock_auth_context
                )

        assert exc_info.value.status_code == 409
        assert "already in use" in exc_info.value.detail

    async def test_request_email_change_email_send_failure(
        self,
        mock_auth_context,
        mock_auth_user,
        mock_redis,
    ):
        """Test email change request when email sending fails."""
        mock_session = AsyncMock()
        mock_repo = AsyncMock(spec=AuthenticationRepository)
        mock_repo.get_by_email.return_value = None
        mock_repo.get_by_id.return_value = mock_auth_user
        mock_repo.update.return_value = None

        request_data = EmailChangeRequestSchema(new_email="newemail@example.com")

        with patch(
            "ehp.core.services.user.AuthenticationRepository", return_value=mock_repo
        ):
            with patch("ehp.core.services.user.send_notification", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await request_email_change(
                        request_data, mock_session, mock_auth_context
                    )

        assert exc_info.value.status_code == 500
        assert "Failed to send verification email" in exc_info.value.detail
        # Should have called update twice: once to set token, once to clear it
        assert mock_repo.update.call_count == 2

    async def test_confirm_email_change_success(self):
        """Test successful email change confirmation."""
        mock_session = AsyncMock()
        mock_repo = AsyncMock(spec=AuthenticationRepository)

        # Mock authentication with valid token
        auth = Authentication(
            id=123,
            user_email="old@example.com",
            pending_email="new@example.com",
            email_change_token="valid_token",
            email_change_token_expires=datetime.now() + timedelta(minutes=10),
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = auth
        mock_session.execute.return_value = mock_result

        mock_repo.update.return_value = None

        with patch(
            "ehp.core.services.user.AuthenticationRepository", return_value=mock_repo
        ):
            with patch("ehp.core.services.user.send_notification", return_value=True):
                result = await confirm_email_change(auth, mock_session)

        assert result.message == "Email address updated successfully"
        assert result.code == 200
        assert auth.user_email == "new@example.com"
        assert auth.pending_email is None
        assert auth.email_change_token is None
        assert auth.email_change_token_expires is None
        mock_repo.update.assert_called_once()

    async def test_confirm_email_change_invalid_token(self):
        """Test email change confirmation with invalid token."""
        mock_session = AsyncMock()

        # Mock database query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        auth = Mock(spec=Authentication)
        auth.email_change_token_expires = None

        with pytest.raises(HTTPException) as exc_info:
            _ = await confirm_email_change(auth, mock_session)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired session" in exc_info.value.detail

    async def test_confirm_email_change_expired_token(self):
        """Test email change confirmation with expired token."""
        mock_session = AsyncMock()
        mock_repo = AsyncMock(spec=AuthenticationRepository)

        # Mock authentication with expired token
        auth = Authentication(
            id=123,
            user_email="old@example.com",
            pending_email="new@example.com",
            email_change_token="expired_token",
            email_change_token_expires=datetime.now()
            - timedelta(minutes=10),  # Expired
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = auth
        mock_session.execute.return_value = mock_result

        mock_repo.update.return_value = None

        auth = Mock(spec=Authentication)
        auth.email_change_token_expires = datetime.now() - timedelta(minutes=10)

        with patch(
            "ehp.core.services.user.AuthenticationRepository", return_value=mock_repo
        ):
            with pytest.raises(HTTPException) as exc_info:
                _ = await confirm_email_change(auth, mock_session)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired session" in exc_info.value.detail
        # Should clean up expired token
        mock_repo.update.assert_called_once_with(auth)
        assert auth.pending_email is None
        assert auth.email_change_token is None

    async def test_confirm_email_change_no_pending_email(self):
        """Test email change confirmation when no pending email exists."""
        mock_session = AsyncMock()

        # Mock authentication without pending email
        auth = Authentication(
            id=123,
            user_email="old@example.com",
            pending_email=None,
            email_change_token="valid_token",
            email_change_token_expires=datetime.now() + timedelta(minutes=10),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = auth
        mock_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            _ = await confirm_email_change(auth, mock_session)

        assert exc_info.value.status_code == 400
        assert "No pending email change found" in exc_info.value.detail
