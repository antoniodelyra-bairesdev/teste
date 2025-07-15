from datetime import datetime, timedelta
from typing import ClassVar
from unittest.mock import patch

import pytest

from ehp.base.jwt_helper import ACCESS_TOKEN_EXPIRE, JWTGenerator
from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.profile import Profile
from ehp.core.models.db.user import User
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.core.services.user import generate_email_change_token
from ehp.db import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils import constants
from ehp.utils.authentication import hash_password
from ehp.utils.date_utils import timezone_now


@pytest.mark.integration
class TestEmailChangeEndpoints:
    """Integration tests for email change endpoints."""

    ORIGINAL_PASSWORD: ClassVar[str] = "Te$tPassword123"

    @pytest.fixture
    async def authenticated_client(
        self, test_client: EHPTestClient, setup_jwt, test_db_manager: DBManager
    ):
        """Setup authenticated client with user."""
        # Create default profiles
        profile_repository = BaseRepository(test_db_manager.get_session(), Profile)
        for profilename, profilecode in constants.PROFILE_IDS.items():
            await profile_repository.create(
                Profile(
                    id=profilecode,
                    name=profilename,
                    code=profilename.lower(),
                )
            )

        # Create authentication and user
        authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd=hash_password(self.ORIGINAL_PASSWORD),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
            profile_id=constants.PROFILE_IDS["user"],
        )

        user = User(
            id=123,
            full_name="Mock User",
            created_at=timezone_now(),
            auth_id=authentication.id,
            email_notifications=True,
        )

        auth_repository = AuthenticationRepository(test_db_manager.get_session())
        user_repository = BaseRepository(test_db_manager.get_session(), User)

        await auth_repository.create(authentication)
        await user_repository.create(user)

        authentication.user = user

        # Create session token
        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            str(authentication.id), authentication.user_email, with_refresh=False
        )
        test_client.auth_token = authenticated_token.access_token

        yield test_client

    async def test_request_email_change_success(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test successful email change request."""
        new_email = "newemail@example.com"

        with patch("ehp.core.services.user.send_notification", return_value=True):
            response = authenticated_client.post(
                "/users/email-change-request",
                json={"new_email": new_email},
                include_auth=True,
            )

        assert response.status_code == 200, response.text

        response_data = response.json()
        assert "Verification email sent" in response_data["message"]
        assert response_data["code"] == 200

        # Verify that the pending email and token were saved
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        auth = await auth_repo.get_by_id(123)
        assert auth is not None
        assert auth.pending_email == new_email
        assert auth.email_change_token is not None
        assert auth.email_change_token_expires is not None

    async def test_request_email_change_same_email(
        self, authenticated_client: EHPTestClient
    ):
        """Test email change request with same email."""
        response = authenticated_client.post(
            "/users/email-change-request",
            json={"new_email": "mock@example.com"},
            include_auth=True,
        )

        assert response.status_code == 400
        assert "must be different" in response.json()["detail"]

    async def test_request_email_change_invalid_email(
        self, authenticated_client: EHPTestClient
    ):
        """Test email change request with invalid email."""
        response = authenticated_client.post(
            "/users/email-change-request",
            json={"new_email": "invalid-email"},
            include_auth=True,
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    async def test_request_email_change_email_in_use(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test email change request with email already in use."""
        # Create another user with the target email
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        existing_auth = Authentication(
            id=456,
            user_name="existing",
            user_email="existing@example.com",
            user_pwd=hash_password("password123"),
            is_active="1",
            is_confirmed="1",
            profile_id=constants.PROFILE_IDS["user"],
        )
        await auth_repo.create(existing_auth)

        response = authenticated_client.post(
            "/users/email-change-request",
            json={"new_email": "existing@example.com"},
            include_auth=True,
        )

        assert response.status_code == 409
        assert "already in use" in response.json()["detail"]

    async def test_request_email_change_email_send_failure(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test email change request when email sending fails."""
        with patch("ehp.core.services.user.send_notification", return_value=False):
            response = authenticated_client.post(
                "/users/email-change-request",
                json={"new_email": "newemail@example.com"},
                include_auth=True,
            )

        assert response.status_code == 500
        assert "Failed to send verification email" in response.json()["detail"]

        # Verify that pending change was cleared
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        auth = await auth_repo.get_by_id(123)
        assert auth.pending_email is None
        assert auth.email_change_token is None

    async def test_request_email_change_unauthenticated(
        self, test_client: EHPTestClient
    ):
        """Test email change request without authentication."""
        response = test_client.post(
            "/users/email-change-request",
            json={"new_email": "newemail@example.com"},
        )

        assert response.status_code == 403

    async def test_confirm_email_change_success(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test successful email change confirmation."""
        # First, setup a pending email change
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        auth = await auth_repo.get_by_id(123)
        assert auth is not None

        token = (
            SessionManager()
            .create_session(
                str(auth.id),
                "confirmed@example.com",
                with_refresh=False,
            )
            .access_token
        )
        auth.pending_email = "confirmed@example.com"
        auth.email_change_token = token
        auth.email_change_token_expires = datetime.now() + timedelta(minutes=30)
        _ = await auth_repo.update(auth)

        # Confirm the change
        with patch("ehp.core.services.user.send_notification", return_value=True):
            response = authenticated_client.get(
                "/users/confirm-email", params={"x-token-auth": token}
            )

        assert response.status_code == 200
        response_data = response.json()
        assert "Email address updated successfully" in response_data["message"]
        assert response_data["code"] == 200

        # Verify email was updated and pending fields cleared
        updated_auth = await auth_repo.get_by_id(123)
        assert updated_auth is not None
        assert updated_auth.user_email == "confirmed@example.com"
        assert updated_auth.pending_email is None
        assert updated_auth.email_change_token is None
        assert updated_auth.email_change_token_expires is None

    async def test_confirm_email_change_invalid_token(
        self, authenticated_client: EHPTestClient
    ):
        """Test email change confirmation with invalid token."""
        response = authenticated_client.get(
            "/users/confirm-email", params={"x-token-auth": "invalid-token"}
        )

        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

    async def test_confirm_email_change_expired_token(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test email change confirmation with expired token."""
        # Setup expired token
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        auth = await auth_repo.get_by_id(123)

        assert auth is not None
        # Create an expired token
        token = (
            SessionManager()
            .create_session(
                str(auth.id),
                "expired@example.com",
                with_refresh=False,
            )
            .access_token
        )
        auth.pending_email = "expired@example.com"
        auth.email_change_token = token
        auth.email_change_token_expires = (
            datetime.now() - ACCESS_TOKEN_EXPIRE - timedelta(minutes=1)
        )  # Expired
        _ = await auth_repo.update(auth)

        response = authenticated_client.get(
            "/users/confirm-email", params={"x-token-auth": token}
        )

        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

        # Verify expired token was cleaned up
        updated_auth = await auth_repo.get_by_id(123)
        assert updated_auth is not None
        assert updated_auth.pending_email is None
        assert updated_auth.email_change_token is None

    async def test_confirm_email_change_no_pending_email(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test email change confirmation when no pending email exists."""
        # Setup token without pending email
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        auth = await auth_repo.get_by_id(123)
        assert auth is not None

        token = (
            SessionManager()
            .create_session(
                str(auth.id),
                "example@test.com",
                with_refresh=False,
            )
            .access_token
        )
        auth.email_change_token = token
        auth.email_change_token_expires = datetime.now() + timedelta(minutes=30)
        # Don't set pending_email
        _ = await auth_repo.update(auth)

        response = authenticated_client.get(
            "/users/confirm-email", params={"x-token-auth": token}
        )

        assert response.status_code == 400
        assert "No pending email change found" in response.json()["detail"]

    async def test_confirm_email_change_missing_token(
        self, authenticated_client: EHPTestClient
    ):
        """Test email change confirmation without token parameter."""
        response = authenticated_client.get("/users/confirm-email")

        assert response.status_code == 403

    async def test_update_user_settings_success(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test successful user settings update."""
        response = authenticated_client.put(
            "/users/settings",
            json={
                "readability_preferences": {"theme": "dark", "font_size": "large"},
                "email_notifications": False,
            },
            include_auth=True,
        )

        assert response.status_code == 204

        # Verify settings were updated
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        user = await user_repo.get_by_id(123)
        assert user is not None
        assert user.readability_preferences == {"theme": "dark", "font_size": "large"}
        assert user.email_notifications is False

    async def test_update_user_settings_partial(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test partial user settings update."""
        response = authenticated_client.put(
            "/users/settings",
            json={"email_notifications": True},
            include_auth=True,
        )

        assert response.status_code == 204

        # Verify only email_notifications was updated
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        user = await user_repo.get_by_id(123)
        assert user is not None
        assert user.email_notifications is True
        assert user.readability_preferences is None  # Should remain unchanged

    async def test_update_user_settings_empty(
        self, authenticated_client: EHPTestClient
    ):
        """Test user settings update with empty payload."""
        response = authenticated_client.put(
            "/users/settings",
            json={},
            include_auth=True,
        )

        assert response.status_code == 204

    async def test_update_user_settings_unauthenticated(
        self, test_client: EHPTestClient
    ):
        """Test user settings update without authentication."""
        response = test_client.put(
            "/users/settings",
            json={"email_notifications": False},
        )

        assert response.status_code == 403

    async def test_complete_email_change_flow(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test complete email change flow from request to confirmation."""
        new_email = "complete@example.com"

        # Step 1: Request email change
        with patch("ehp.core.services.user.send_notification", return_value=True):
            request_response = authenticated_client.post(
                "/users/email-change-request",
                json={"new_email": new_email},
                include_auth=True,
            )

        assert request_response.status_code == 200

        # Get the token from database
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        auth = await auth_repo.get_by_id(123)
        assert auth is not None

        token = auth.email_change_token

        # Step 2: Confirm email change
        with patch("ehp.core.services.user.send_notification", return_value=True):
            confirm_response = authenticated_client.get(
                "/users/confirm-email",
                include_auth=False,
                params={"x-token-auth": token},
            )

        assert confirm_response.status_code == 200
        assert (
            "Email address updated successfully" in confirm_response.json()["message"]
        )

        # Verify final state
        updated_auth = await auth_repo.get_by_id(123)
        assert updated_auth is not None
        assert updated_auth.user_email == new_email
        assert updated_auth.pending_email is None
        assert updated_auth.email_change_token is None
