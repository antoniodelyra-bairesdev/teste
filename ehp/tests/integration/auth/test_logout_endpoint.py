from unittest.mock import patch, Mock

import pytest

from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password


@pytest.mark.integration
class TestLogoutEndpoint:
    @pytest.fixture
    async def authenticated_client(
        self, test_client: EHPTestClient, setup_jwt, test_db_manager: DBManager
    ):
        authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd=hash_password("testpassword"),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
        )
        user = User(
            id=123,
            full_name="Mock User",
            created_at=None,
            auth_id=authentication.id,
        )
        auth_repository = AuthenticationRepository(
            test_db_manager.get_session(), Authentication
        )
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        await auth_repository.create(authentication)
        await user_repository.create(user)
        authentication.user = user
        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            authentication.id, authentication.user_email, with_refresh=False
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    def test_logout_success(self, authenticated_client: EHPTestClient):
        response = authenticated_client.post("/logout", include_auth=True)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"
        assert data["status_code"] == 200

    @patch("ehp.core.services.logout.SessionManager")
    @patch("ehp.core.services.logout.log_error")
    def test_logout_session_manager_exception(
        self,
        mock_log_error,
        mock_session_manager_class,
        authenticated_client: EHPTestClient,
    ):
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager
        mock_session_manager.remove_session_from_token.side_effect = Exception(
            "Session removal failed"
        )
        response = authenticated_client.post("/logout", include_auth=True)
        assert response.status_code == 500
        assert response.json()["detail"] == "An error occurred during logout"
        mock_log_error.assert_called_once()

    def test_logout_missing_token_header(self, authenticated_client: EHPTestClient):
        response = authenticated_client.post("/logout")
        assert response.status_code == 422
        assert "detail" in response.json()

    @patch("ehp.core.services.logout.SessionManager")
    @patch("ehp.core.services.logout.log_error")
    def test_logout_unexpected_error(
        self,
        mock_log_error,
        mock_session_manager_class,
        authenticated_client: EHPTestClient,
    ):
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager
        mock_session_manager.remove_session_from_token.side_effect = RuntimeError(
            "Unexpected error"
        )
        response = authenticated_client.post("/logout", include_auth=True)
        assert response.status_code == 500
        assert response.json()["detail"] == "An error occurred during logout"
        mock_log_error.assert_called_once()
