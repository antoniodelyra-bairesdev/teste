from datetime import timedelta
from typing import ClassVar
import pytest
from ehp.core.models.db.profile import Profile
from ehp.core.services.password import generate_reset_token
from ehp.db import DBManager
from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.tests.integration.conftest import AuthenticatedClientProxy
from ehp.tests.utils.test_client import EHPTestClient
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.utils import constants
from ehp.utils.authentication import check_password, hash_password
from ehp.utils.date_utils import timezone_now


@pytest.mark.integration
class TestUpdatePasswordForResetEndpoint:
    ORIGINAL_PASSWORD: ClassVar[str] = "Te$tPassword123"
    RESET_TOKEN: ClassVar[str] = generate_reset_token()

    @pytest.fixture
    async def authenticated_client(
        self, test_client: EHPTestClient, setup_jwt, test_db_manager: DBManager
    ):
        profile_repository = BaseRepository(test_db_manager.get_session(), Profile)
        for profilename, profilecode in constants.PROFILE_IDS.items():
            _ = await profile_repository.create(
                Profile(
                    id=profilecode,
                    name=profilename,
                    code=profilename.lower(),
                )
            )

        authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd=hash_password(self.ORIGINAL_PASSWORD),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
            profile_id=constants.PROFILE_IDS["user"],
            reset_token=self.RESET_TOKEN,
            reset_token_expires=timezone_now() + timedelta(days=1),
        )
        user = User(
            id=123,
            full_name="Mock User",
            created_at=None,
            auth_id=authentication.id,
        )
        auth_repository = AuthenticationRepository(test_db_manager.get_session())
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        _ = await auth_repository.create(authentication)
        _ = await user_repository.create(user)
        authentication.user = user
        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            str(authentication.id), authentication.user_email, with_refresh=False
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    @pytest.mark.parametrize(
        "weak_password,expected_error",
        [
            ("short", "Password must be at least 8 characters"),
            ("password123", "Password must contain at least one uppercase letter"),
            ("PASSWORD123", "Password must contain at least one lowercase letter"),
            ("NoNumbersHere", "Password must contain at least one digit"),
            (
                "NoSpecialChar1",
                "Password must contain at least one special character",
            ),
            (ORIGINAL_PASSWORD, "New password cannot be the same as the old password."),
        ],
        ids=[
            "Checking for password length",
            "Checking for upper case",
            "Checking for lower case",
            "Checking for digit",
            "Checking for special character",
            "Checking for same password",
        ],
    )
    async def test_change_password_validates_for_password_input_strength(
        self,
        authenticated_client: EHPTestClient,
        weak_password: str,
        expected_error: str,
    ):
        response = authenticated_client.put(
            "/users/password/123",
            json={
                "new_password": weak_password,
                "reset_token": self.RESET_TOKEN,
                "logout": True,
            },
            include_auth=False,
        )

        assert response.status_code in (409, 422), (
            "Expected validation error, but request succeeded"
        )

        response_data = response.json()

        if response.status_code == 409:
            assert "detail" in response_data, "Response should contain 'detail' key"
            assert expected_error in response_data["detail"], (
                f"Expected error message '{expected_error}' not found in response, found: {response_data['detail']}"
            )
        else:
            # For status code 422, the error message might be in a different format
            assert isinstance(response_data["detail"], list), (
                "Expected 'detail' to be a list for validation errors"
            )
            assert len(response_data["detail"]) > 0, (
                "Expected 'detail' to contain at least one error message"
            )
            assert expected_error in response_data["detail"][0]["msg"], (
                f"Expected error message '{expected_error}' not found in response, found: {response_data['detail'][0]['msg']}"
            )

    async def test_change_password_by_id_success(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        new_password = "NewPa$sword123"

        response = authenticated_client.put(
            "/users/password/123",
            json={
                "new_password": new_password,
                "reset_token": self.RESET_TOKEN,
                "logout": True,
            },
            include_auth=False,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for successful password change"
        )

        # Verify the password was changed in the database
        db_session = test_db_manager.get_session()
        auth_repo: AuthenticationRepository = AuthenticationRepository(db_session)
        user = await auth_repo.get_by_id(123)
        assert user is not None
        assert not check_password(user.user_pwd, self.ORIGINAL_PASSWORD), (
            "Original password should not match"
        )
        assert check_password(user.user_pwd, new_password), "New password should match"
        assert (user.reset_token, user.reset_token_expires) == (None, None)

        # Verify that the session is invalidated
        session_manager = SessionManager()
        session_data = session_manager.get_session_from_token(
            authenticated_client.auth_token
        )
        assert session_data is None

    async def test_change_password_by_id_invalid_token(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        new_password = "NewPa$sword123"

        # Attempt to change password for a different user (ID 456)
        response = authenticated_client.put(
            "/users/password/123",
            json={
                "new_password": new_password,
                "reset_token": generate_reset_token(),
                "logout": True,
            },
            include_auth=False,
        )
        assert response.status_code == 403, "Expected 403 Forbidden status code"

        # Verify the password was not changed in the database
        db_session = test_db_manager.get_session()
        auth_repo: AuthenticationRepository = AuthenticationRepository(db_session)
        user = await auth_repo.get_by_id(123)
        assert user is not None
        assert check_password(user.user_pwd, self.ORIGINAL_PASSWORD), (
            "Password should remain unchanged"
        )

    async def test_change_password_by_id_expired_token(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        new_password = "NewPa$sword123"
        # Set the reset token to an expired state
        auth_repo = AuthenticationRepository(test_db_manager.get_session())
        user = await auth_repo.get_by_id(123)
        assert user is not None, "User with ID 123 should exist"
        user.reset_token_expires = timezone_now() - timedelta(days=1)
        _ = await auth_repo.update(user)

        # Attempt to change password with an expired token
        response = authenticated_client.put(
            "/users/password/123",
            json={
                "new_password": new_password,
                "reset_token": self.RESET_TOKEN,
                "logout": True,
            },
            include_auth=False,
        )
        assert response.status_code == 403, "Expected 403 Forbidden status code"

    async def test_change_password_other_id_not_found(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        new_password = "NewPa$sword123"

        auth_repo = AuthenticationRepository(test_db_manager.get_session())

        assert await auth_repo.get_by_id(456) is None, (
            "User with ID 456 should not exist"
        )

        # Change password for the user with ID 456
        # This user does not exist, so it should return 404
        response = authenticated_client.put(
            "/users/password/456",
            json={
                "new_password": new_password,
                "reset_token": self.RESET_TOKEN,
                "logout": True,
            },
            include_auth=False,
        )
        assert response.status_code == 404, "Expected 404 for non-existent user"
        assert response.json() == {"detail": "User not found."}, (
            "Expected 'User not found.' message"
        )


@pytest.mark.integration
class TestUpdateUserSettingsEndpoint:
    ORIGINAL_PASSWORD: ClassVar[str] = "Te$tPassword123"
    RESET_TOKEN: ClassVar[str] = "mock-123"

    @pytest.fixture
    async def authenticated_client(
        self,
        test_client: EHPTestClient,
        setup_jwt,
        test_db_manager: DBManager,
    ):
        profile_repository = BaseRepository(test_db_manager.get_session(), Profile)
        for profilename, profilecode in constants.PROFILE_IDS.items():
            _ = await profile_repository.create(
                Profile(
                    id=profilecode,
                    name=profilename,
                    code=profilename.lower(),
                )
            )

        authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd=hash_password(self.ORIGINAL_PASSWORD),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
            profile_id=constants.PROFILE_IDS["user"],
            reset_token=self.RESET_TOKEN,
            reset_token_expires=timezone_now() + timedelta(days=1),
        )
        user = User(
            id=123,
            full_name="Mock User",
            created_at=None,
            auth_id=authentication.id,
        )
        auth_repository = AuthenticationRepository(test_db_manager.get_session())
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        _ = await auth_repository.create(authentication)
        _ = await user_repository.create(user)
        authentication.user = user
        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            str(authentication.id), authentication.user_email, with_refresh=False
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    async def test_update_user_settings(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        response = authenticated_client.put(
            "/users/settings",
            json={
                "readability_preferences": {"theme": "dark"},
                "email_notifications": False,
            },
            include_auth=True,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for successful settings update"
        )

        # Verify the settings were updated in the database
        db_session = test_db_manager.get_session()
        user_repo = BaseRepository(db_session, User)
        user = await user_repo.get_by_id(123)
        assert user is not None
        assert user.readability_preferences == {"theme": "dark"}
        assert user.email_notifications is False

    async def test_update_user_settings_no_changes(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        # Attempt to update settings with no changes
        response = authenticated_client.put(
            "/users/settings",
            json={},
            include_auth=True,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for no changes in settings"
        )

        # Verify the settings remain unchanged in the database
        db_session = test_db_manager.get_session()
        user_repo = BaseRepository(db_session, User)
        user = await user_repo.get_by_id(123)
        assert user is not None
        assert user.readability_preferences is None
        assert user.email_notifications is True


@pytest.mark.integration
class TestOnboardingStatusEndpoint:
    async def test_get_onboarding_status_returns_status_false_for_brand_new_user(
        self, authenticated_client: AuthenticatedClientProxy
    ):
        response = authenticated_client.get(
            "/users/me/onboarding-status", include_auth=True
        )
        assert response.status_code == 200, (
            "Expected 200 status code for getting onboarding status"
        )
        assert response.json()["onboarding_complete"] is False, (
            "Expected onboarding status to be False for a brand new user"
        )

    async def test_get_onboarding_status_returns_true_for_manually_updated_user(
        self, authenticated_client: AuthenticatedClientProxy
    ):
        authenticated_client.user.onboarding_complete = True
        response = authenticated_client.get(
            "/users/me/onboarding-status", include_auth=True
        )
        assert response.status_code == 200, (
            "Expected 200 status code for getting onboarding status"
        )
        assert response.json()["onboarding_complete"] is True, (
            "Expected onboarding status to be True for a manually updated user"
        )

    async def test_put_onboarding_status_updates_status(
        self, authenticated_client: AuthenticatedClientProxy
    ):
        response = authenticated_client.put(
            "/users/me/onboarding-status",
            json={"onboarding_complete": True},
            include_auth=True,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for successful onboarding status update"
        )

        # Verify the onboarding status was updated
        response = authenticated_client.get(
            "/users/me/onboarding-status", include_auth=True
        )
        assert response.status_code == 200, (
            "Expected 200 status code for getting onboarding status after update"
        )
        assert response.json()["onboarding_complete"] is True, (
            "Expected onboarding status to be True after update"
        )

    async def test_put_onboarding_status_returns_forbidden_for_unauthenticated_user(
        self, test_client: EHPTestClient
    ):
        response = test_client.put(
            "/users/me/onboarding-status",
            json={"onboarding_complete": True},
            include_auth=False,
        )
        assert response.status_code == 403, (
            "Expected 403 status code for unauthenticated user trying to update onboarding status"
        )

    async def test_put_onboarding_disables_status(
        self, authenticated_client: AuthenticatedClientProxy
    ):
        response = authenticated_client.put(
            "/users/me/onboarding-status",
            json={"onboarding_complete": False},
            include_auth=True,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for successful onboarding status update"
        )

        # Verify the onboarding status was updated
        response = authenticated_client.get(
            "/users/me/onboarding-status", include_auth=True
        )
        assert response.status_code == 200, (
            "Expected 200 status code for getting onboarding status after update"
        )
        assert response.json()["onboarding_complete"] is False, (
            "Expected onboarding status to be False after update"
        )

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/users/me/onboarding-status"),
            ("put", "/users/me/onboarding-status"),
            ("post", "/users/me/onboarding-status/reset"),
        ],
        ids=[
            "get_onboarding_status",
            "put_onboarding_status",
            "post_reset_onboarding_status",
        ],
    )
    async def test_onboarding_endpoints_require_authentication(
        self, authenticated_client: AuthenticatedClientProxy, method: str, path: str
    ):
        # Test that the endpoint requires authentication
        response = getattr(authenticated_client, method)(path, include_auth=False)
        assert response.status_code == 403, (
            f"Expected 403 status code for unauthenticated {method.upper()} request to {path}"
        )

    async def test_post_resets_onboarding_status(
        self, authenticated_client: AuthenticatedClientProxy
    ):
        # First, set onboarding status to True
        response = authenticated_client.put(
            "/users/me/onboarding-status",
            json={"onboarding_complete": True},
            include_auth=True,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for successful onboarding status update"
        )

        # Now reset the onboarding status
        response = authenticated_client.post(
            "/users/me/onboarding-status/reset",
            include_auth=True,
        )
        assert response.status_code == 204, (
            "Expected 204 status code for successful onboarding status reset"
        )

        # Verify the onboarding status was reset
        response = authenticated_client.get(
            "/users/me/onboarding-status", include_auth=True
        )
        assert response.status_code == 200, (
            "Expected 200 status code for getting onboarding status after reset"
        )
        assert response.json()["onboarding_complete"] is False, (
            "Expected onboarding status to be False after reset"
        )
