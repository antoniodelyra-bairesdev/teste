from dataclasses import dataclass
from datetime import timedelta

import pytest

from ehp.base.jwt_helper import TokenPayload
from ehp.base.session import SessionManager
from ehp.core.models.db import Authentication, User
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.core.services.session import AuthContext
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password
from ehp.utils.constants import AUTH_INACTIVE
from ehp.utils.date_utils import timezone_now


@dataclass
class AuthContainer:
    authentication: Authentication
    user: User
    token_payload: TokenPayload
    session_manager: SessionManager


@pytest.fixture
async def mock_authentication(
    test_client: EHPTestClient, test_db_manager: DBManager, setup_jwt
) -> AuthContainer:
    authentication = Authentication(
        id=123,
        user_name="mockuser",
        user_email="mock@example.com",
        user_pwd=hash_password("testpassword"),  # Using actual hash_password utility
        is_active="1",
        is_confirmed="1",
        retry_count=0,
    )
    user = User(
        id=123,
        full_name="Mock User",
        created_at=timezone_now(),
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
        str(authentication.id), authentication.user_email, with_refresh=False
    )
    test_client.auth_token = authenticated_token.access_token
    return AuthContainer(
        authentication=authentication,
        user=user,
        token_payload=authenticated_token,
        session_manager=session_manager,
    )


@pytest.mark.integration
class TestSessionDependency:
    """Integration tests for session dependency"""

    def test_route_works_as_expected_with_valid_authentication(
        self, test_client: EHPTestClient, mock_authentication: AuthContainer
    ):
        """Test that the route works with valid authentication."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        response = test_client.get("/mocked-route", include_auth=True)
        assert response.status_code == 200
        assert response.json() == {
            "auth_id": mock_authentication.authentication.id,
            "user_id": mock_authentication.user.id,
            "user_email": mock_authentication.authentication.user_email,
        }

    def test_route_fails_with_missing_authentication(self, test_client: EHPTestClient):
        """Test that the route fails with invalid authentication."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        # Simulate invalid authentication by clearing the auth token
        response = test_client.get("/mocked-route", include_auth=False)
        assert response.status_code == 403
        assert response.json() == {"detail": "Not authenticated"}

    def test_route_fails_with_invalid_token(self, test_client: EHPTestClient):
        """Test that the route fails with invalid token."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        # Simulate invalid authentication by using an invalid token
        test_client.auth_token = "invalid_token"
        response = test_client.get("/mocked-route", include_auth=True)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or expired session"}

    def test_route_fails_with_invalid_token_if_session_is_invalidated(
        self, test_client: EHPTestClient, mock_authentication: AuthContainer
    ):
        """Test that the route fails with invalid token if session is invalidated."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        # Invalidate the session
        mock_authentication.session_manager.remove_session_from_token(
            mock_authentication.token_payload.access_token
        )
        # Now try to access the route with the invalidated session
        response = test_client.get("/mocked-route", include_auth=True)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or expired session"}

    def test_route_fails_with_expired_token(
        self, test_client: EHPTestClient, mock_authentication: AuthContainer
    ):
        """Test that the route fails with expired token."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        # Replace the token with an expired one
        expired_time = timezone_now() - timedelta(days=500)
        expired_token, _ = (
            mock_authentication.session_manager.jwt_generator.encode_access_token(
                user_id=str(mock_authentication.authentication.id),
                email=mock_authentication.authentication.user_email,
                jti=mock_authentication.session_manager.jwt_generator.generate_jti(
                    mock_authentication.authentication.user_email, expired_time
                ),
                issued_at=expired_time,
            )
        )
        test_client.auth_token = expired_token
        response = test_client.get("/mocked-route", include_auth=True)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or expired session"}

    async def test_route_fails_with_valid_token_but_unexistent_user(
        self,
        test_client: EHPTestClient,
        mock_authentication: AuthContainer,
        test_db_manager: DBManager,
    ):
        """Test that the route fails with valid token but unexistent user."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        # Simulate a user that does not exist
        auth_repository = AuthenticationRepository(
            test_db_manager.get_session(), Authentication
        )
        await auth_repository.delete(mock_authentication.authentication.id)
        response = test_client.get("/mocked-route", include_auth=True)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or expired session"}

    async def test_route_fails_with_valid_token_but_inactive_user(
        self,
        test_client: EHPTestClient,
        mock_authentication: AuthContainer,
        test_db_manager: DBManager,
    ):
        """Test that the route fails with valid token but inactive user."""

        @test_client.app.get("/mocked-route")
        def mocked_route(ctx: AuthContext):
            return {
                "auth_id": ctx.id,
                "user_id": ctx.user.id,
                "user_email": ctx.user_email,
            }

        # Simulate an inactive user
        mock_authentication.authentication.is_active = AUTH_INACTIVE
        auth_repository = AuthenticationRepository(
            test_db_manager.get_session(), Authentication
        )
        await auth_repository.update(mock_authentication.authentication)
        response = test_client.get("/mocked-route", include_auth=True)
        assert response.status_code == 403
        assert response.json() == {"detail": "User account is not active"}
