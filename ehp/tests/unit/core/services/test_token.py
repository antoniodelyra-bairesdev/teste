import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from starlette import status

from ehp.core.services.token import login_for_access_token
from ehp.core.models.schema.token import TokenRequestData
from ehp.core.models.db.authentication import Authentication
from ehp.base.jwt_helper import TokenPayload
from ehp.utils.constants import AUTH_ACTIVE, AUTH_CONFIRMED


class TestTokenService:
    """Unit tests for token service functionality."""

    @pytest.fixture
    def valid_token_data(self):
        return TokenRequestData(username="test@example.com", password="validpassword")

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 123
        user.user_email = "test@example.com"
        user.user_name = "testuser"
        user.user_pwd = "hashed_password"
        user.is_active = AUTH_ACTIVE
        user.is_confirmed = AUTH_CONFIRMED
        return user

    @pytest.fixture
    def mock_token_payload(self):
        return TokenPayload(
            access_token="mock_access_token",
            token_type="Bearer",
            expires_at=3600
        )

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.log_error")
    @patch("ehp.core.services.token.SessionManager")
    @patch("ehp.core.services.token.check_password")
    @patch("ehp.core.services.token.DBManager")
    async def test_login_success_with_email(
        self, mock_db_manager, mock_check_password, mock_session_manager, mock_log_error,
        valid_token_data, mock_user, mock_token_payload
    ):
        """Test successful login using email."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = mock_user
        mock_auth_repo.get_by_username.return_value = None
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            mock_check_password.return_value = True
            mock_session_manager_instance = MagicMock()
            mock_session_manager.return_value = mock_session_manager_instance
            mock_session_manager_instance.create_session.return_value = mock_token_payload

            # Execute
            response = await login_for_access_token(valid_token_data)

            # Verify
            assert response.status_code == status.HTTP_200_OK
            response_data = response.body.decode()
            assert "mock_access_token" in response_data
            mock_auth_repo.get_by_email.assert_called_once_with("test@example.com")
            mock_check_password.assert_called_once_with("hashed_password", "validpassword")
            mock_session_manager_instance.create_session.assert_called_once_with(
                user_id="123", email="test@example.com", with_refresh=False
            )

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.SessionManager")
    @patch("ehp.core.services.token.check_password")
    @patch("ehp.core.services.token.DBManager")
    async def test_login_success_with_username(
        self, mock_db_manager, mock_check_password, mock_session_manager,
        mock_user, mock_token_payload
    ):
        """Test successful login using username when email lookup fails."""
        token_data = TokenRequestData(username="testuser", password="validpassword")
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = None
        mock_auth_repo.get_by_username.return_value = mock_user
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            mock_check_password.return_value = True
            mock_session_manager_instance = MagicMock()
            mock_session_manager.return_value = mock_session_manager_instance
            mock_session_manager_instance.create_session.return_value = mock_token_payload

            # Execute
            response = await login_for_access_token(token_data)

            # Verify
            assert response.status_code == status.HTTP_200_OK
            mock_auth_repo.get_by_email.assert_called_once_with("testuser")
            mock_auth_repo.get_by_username.assert_called_once_with("testuser")

    @pytest.mark.asyncio
    async def test_login_missing_username(self):
        """Test login with missing username."""
        token_data = TokenRequestData(username="", password="validpassword")
        
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(token_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username and password are required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_login_missing_password(self):
        """Test login with missing password."""
        token_data = TokenRequestData(username="test@example.com", password="")
        
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(token_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username and password are required" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.DBManager")
    async def test_login_user_not_found(self, mock_db_manager):
        """Test login when user is not found."""
        token_data = TokenRequestData(username="nonexistent@example.com", password="password")
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = None
        mock_auth_repo.get_by_username.return_value = None
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(token_data)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.DBManager")
    async def test_login_inactive_user(self, mock_db_manager, mock_user):
        """Test login with inactive user account."""
        token_data = TokenRequestData(username="test@example.com", password="password")
        mock_user.is_active = "0"  # Inactive
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = mock_user
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(token_data)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Account is deactivated" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.DBManager")
    async def test_login_unconfirmed_user(self, mock_db_manager, mock_user):
        """Test login with unconfirmed user account."""
        token_data = TokenRequestData(username="test@example.com", password="password")
        mock_user.is_confirmed = "0"  # Unconfirmed
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = mock_user
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(token_data)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Account is not confirmed" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.check_password")
    @patch("ehp.core.services.token.DBManager")
    async def test_login_invalid_password(self, mock_db_manager, mock_check_password, mock_user):
        """Test login with invalid password."""
        token_data = TokenRequestData(username="test@example.com", password="wrongpassword")
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = mock_user
        mock_check_password.return_value = False
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(token_data)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.log_error")
    @patch("ehp.core.services.token.DBManager")
    async def test_login_database_error(self, mock_db_manager, mock_log_error):
        """Test login when database error occurs."""
        token_data = TokenRequestData(username="test@example.com", password="password")
        
        # Setup mock to raise exception
        mock_db_manager.side_effect = Exception("Database connection failed")
        
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(token_data)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in exc_info.value.detail
        mock_log_error.assert_called_once()

    @pytest.mark.asyncio
    @patch("ehp.core.services.token.log_error")
    @patch("ehp.core.services.token.SessionManager")
    @patch("ehp.core.services.token.check_password")
    @patch("ehp.core.services.token.DBManager")
    async def test_login_session_creation_error(
        self, mock_db_manager, mock_check_password, mock_session_manager, mock_log_error,
        valid_token_data, mock_user
    ):
        """Test login when session creation fails."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_db_manager.return_value.transaction.return_value.__aenter__.return_value = mock_session
        
        mock_auth_repo = AsyncMock()
        mock_auth_repo.get_by_email.return_value = mock_user
        mock_check_password.return_value = True
        
        mock_session_manager_instance = MagicMock()
        mock_session_manager.return_value = mock_session_manager_instance
        mock_session_manager_instance.create_session.side_effect = Exception("Session creation failed")
        
        with patch("ehp.core.services.token.AuthenticationRepository", return_value=mock_auth_repo):
            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(valid_token_data)
            
            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Internal server error" in exc_info.value.detail
            mock_log_error.assert_called_once()
