from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI

from ehp.base.jwt_helper import JWTGenerator, TokenPayload
from ehp.base.redis_storage import get_redis_client
from ehp.core.services.session import get_authentication
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password
from ehp.utils.base import base64_encrypt


@pytest.mark.end_to_end
@pytest.mark.usefixtures("setup_jwt")
def test_auth_and_logout_flow(test_client: EHPTestClient):
    """
    Test a complete authentication flow:
    1. User authenticates
    2. User accesses a protected endpoint
    3. User logs out
    4. User is denied access to protected endpoint
    """

    @test_client.app.get("/mock", dependencies=[Depends(get_authentication)])
    def mock_endpoint():
        """
        Mock endpoint to test authentication.
        Requires user session to be valid.
        """
        return {"message": "This is a protected endpoint"}

    # Setup authentication mocks
    user_pwd_hash = hash_password("testpassword")
    user_data = {
        "id": 1,
        "user_name": "testuser",
        "user_email": "test@example.com",
        "user_pwd": user_pwd_hash,
        "is_active": "1",
        "is_confirmed": "1",
        "profile_id": 1,
        "person": {
            "id": 1,
            "first_name": "Test",
            "last_name": "User",
            "language_id": 1,
            "students": [],
        },
    }

    auth_email_patch, auth_username_patch, mock_auth = test_client.setup_authentication(
        user_data
    )
    auth_by_id_patch = patch(
        "ehp.core.repositories.AuthenticationRepository.get_by_id",
        return_value=mock_auth
    )

    # Start patches
    auth_email_patch.start()
    auth_by_id_patch.start()
    auth_username_patch.start()

    # Step 1: User authenticates
    login_response = test_client.post(
        "/token",
        json={
            "user_name": "testuser",
            "username": "test@example.com",
            "password": "testpassword",
        },
    )

    assert login_response.status_code == 200
    # Should return a valid token_payload
    session_token = TokenPayload.model_validate_json(login_response.text)

    # Save the token for later requests
    test_client.auth_token = session_token.access_token

    # Step 2: User accesses a protected endpoint
    protected_response = test_client.get("/mock", include_auth=True)
    # assert False, protected_response.text
    assert protected_response.status_code == 200

    # Step 4: Configure mock to simulate invalid session after logout
    redis_client = get_redis_client()
    decoded_token = JWTGenerator().decode_token(
        session_token.access_token, verify_exp=False
    )
    session_id = decoded_token["jti"]
    redis_client.delete(session_id)

    # User is denied access to protected endpoint
    protected_response = test_client.get("/mock", include_auth=True)
    assert protected_response.status_code == 401
    assert "Invalid or expired session" in protected_response.json()["detail"]

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()
    auth_by_id_patch.stop()


@pytest.mark.skip(reason="This is not implemented yet.")
def test_password_reset_flow(app: FastAPI):
    """
    Test a complete password reset flow:
    1. User requests password reset
    2. User validates reset code
    3. User sets new password
    """
    client = EHPTestClient(app)

    # Setup authentication mocks
    user_pwd_hash = hash_password("oldpassword")
    user_data = {
        "id": 1,
        "user_name": "testuser",
        "user_email": "test@example.com",
        "user_pwd": user_pwd_hash,
        "is_active": "1",
        "is_confirmed": "1",
        "reset_password": "0",
        "reset_code": None,
        "profile_id": 1,
        "person": {"id": 1, "language_id": 1},
    }

    auth_email_patch, auth_username_patch, mock_auth = client.setup_authentication(
        user_data
    )

    # Start patches
    auth_email_patch.start()
    auth_username_patch.start()

    with patch("ehp.utils.email.send_notification", return_value=True):
        # Step 1: User requests password reset
        reset_response = client.post(
            "/user/pwd", json={"auth_id": 1, "user_email": "test@example.com"}
        )

        assert reset_response.status_code == 200
        assert reset_response.json()["result"]["CODE"] == 200

        # Verify that reset code was generated and set
        assert mock_auth.reset_password == "1"
        assert mock_auth.reset_code is not None

        reset_code = mock_auth.reset_code

        # Step 2: User validates reset code
        validate_response = client.put(
            "/user/validate/code", json={"auth_id": 1, "reset_code": reset_code}
        )

        assert validate_response.status_code == 200
        assert validate_response.json()["result"]["code_is_valid"] is True

        # Step 3: User sets new password
        new_password = "newpassword"
        reset_pwd_response = client.put(
            "/user/pwd/reset",
            json={
                "auth_id": 1,
                "user_email": "test@example.com",
                "user_password": base64_encrypt(new_password).decode("utf-8"),
            },
        )

        assert reset_pwd_response.status_code == 200
        assert reset_pwd_response.json()["result"]["CODE"] == 200

        # Verify password was updated and reset flags were cleared
        assert mock_auth.reset_password == "0"
        assert mock_auth.reset_code is None

        # Verify the new password hash works
        from ehp.utils.authentication import check_password

        assert check_password(mock_auth.user_pwd, new_password)

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()


@pytest.mark.end_to_end
def test_request_password_reset_flow(app: FastAPI):
    """
    Test the new password reset request endpoint:
    1. Create a user in the system
    2. User requests password reset via /password-reset/request
    3. Verify email is sent and token is generated
    4. Test with non-existent email (should still return success for security)
    """
    client = EHPTestClient(app)

    # Create a mock authentication object
    mock_auth = MagicMock()
    mock_auth.id = 1
    mock_auth.user_name = "testuser"
    mock_auth.user_email = "test@example.com"
    mock_auth.user_pwd = hash_password("originalpassword")
    mock_auth.is_active = "1"
    mock_auth.is_confirmed = "1"
    mock_auth.profile_id = 1
    mock_auth.reset_token = None
    mock_auth.reset_token_expires = None
    mock_auth.reset_password = "0"

    # Mock the repository update method and ensure email is mocked
    with patch("ehp.core.repositories.authentication.AuthenticationRepository.update") as mock_update, \
         patch("ehp.core.repositories.authentication.AuthenticationRepository.get_by_email") as mock_get_by_email, \
         patch("ehp.utils.email.send_mail") as mock_send_html_mail:
        
        # Configure mocks (email is already mocked by EHPTestClient)
        mock_get_by_email.return_value = mock_auth
        mock_update.return_value = None

        # Step 1: User requests password reset with valid email
        reset_response = client.post(
            "/password-reset/request",
            json={"user_email": "test@example.com"}
        )

        assert reset_response.status_code == 200
        assert reset_response.json()["result"]["CODE"] == 200

        # Verify that the repository methods were called
        mock_get_by_email.assert_called_with("test@example.com")
        mock_update.assert_called_once()
        
        # Verify that reset token was set on the auth object
        assert mock_auth.reset_token is not None
        assert len(mock_auth.reset_token) == 64  # 32 bytes hex = 64 characters
        assert mock_auth.reset_token_expires is not None
        assert mock_auth.reset_password == "1"

        # Verify email was attempted to be sent (send_html_mail was called)
        mock_send_html_mail.assert_called_once()

        # Reset mocks for next test
        mock_get_by_email.reset_mock()
        mock_update.reset_mock()
        mock_send_html_mail.reset_mock()

        # Step 2: Test with non-existent email (should return success for security)
        mock_get_by_email.return_value = None

        reset_response_nonexistent = client.post(
            "/password-reset/request",
            json={"user_email": "nonexistent@example.com"}
        )

        assert reset_response_nonexistent.status_code == 200
        assert reset_response_nonexistent.json()["result"]["CODE"] == 200

        # Verify repository was called but no update or email was sent
        mock_get_by_email.assert_called_with("nonexistent@example.com")
        mock_update.assert_not_called()
        mock_send_html_mail.assert_not_called()


@pytest.mark.end_to_end
def test_register_and_login_flow(app: FastAPI):
    """
    Test a complete user registration and login flow:
    1. Register a new user
    2. Login with the registered credentials
    """
    client = EHPTestClient(app)

    # Create mock objects with proper to_dict methods
    mock_auth = MagicMock()
    mock_auth.id = 1
    mock_auth.user_name = "test@example.com"
    mock_auth.user_email = "test@example.com"
    mock_auth.is_active = "1"
    mock_auth.is_confirmed = "0"
    mock_auth.profile_id = 1

    async def mock_auth_to_dict():
        return {
            "id": 1,
            "user_name": "test@example.com",
            "user_email": "test@example.com",
            "is_active": "1",
            "is_confirmed": "0",
            "profile_id": 1
        }
    mock_auth.to_dict = mock_auth_to_dict

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.full_name = "Test User"
    mock_user.auth_id = 1

    async def mock_user_to_dict():
        return {
            "id": 1,
            "full_name": "Test User",
            "auth_id": 1
        }
    mock_user.to_dict = mock_user_to_dict

    mock_profile = MagicMock()
    mock_profile.id = 1

    # Step 1: Mock the registration endpoint response
    with patch("ehp.core.repositories.authentication.AuthenticationRepository.get_by_email", return_value=None), \
         patch("ehp.core.repositories.authentication.AuthenticationRepository.create", return_value=mock_auth), \
         patch("sqlalchemy.ext.asyncio.AsyncSession.get", return_value=mock_profile), \
         patch("sqlalchemy.ext.asyncio.AsyncSession.add"), \
         patch("sqlalchemy.ext.asyncio.AsyncSession.flush"), \
         patch("ehp.core.models.db.Authentication", MagicMock), \
         patch("ehp.core.models.db.User", return_value=mock_user), \
         patch("ehp.core.models.db.Profile", MagicMock):

        # Register user
        registration_data = {
            "user_name": "Test User",
            "user_email": "test@example.com",
            "user_password": "TestPassword123"
        }

        register_response = client.post("/register", json=registration_data)

        assert register_response.status_code == 200
        response_data = register_response.json()
        assert response_data["result"]["code"] == 200
        assert response_data["result"]["message"] == "User registered successfully"
        assert response_data["result"]["auth"]["user_email"] == "test@example.com"

    # Step 2: Setup login mocks
    user_pwd_hash = hash_password("TestPassword123")
    login_user_data = {
        "id": 1,
        "user_name": "test@example.com",
        "user_email": "test@example.com",
        "user_pwd": user_pwd_hash,
        "is_active": "1",
        "is_confirmed": "1",  # Set as confirmed for login
        "profile_id": 1
    }

    auth_email_patch, auth_username_patch, mock_auth_login = client.setup_authentication(login_user_data)

    # Create a mock TokenPayload for the session
    mock_token_payload = TokenPayload(access_token="mock_token", refresh_token=None, token_type="bearer", expires_at=600)
    mock_token_payload.access_token = "mock-token-12345"

    # Mock the entire SessionManager class
    mock_session_manager = MagicMock()
    mock_session_manager.create_session.return_value = mock_token_payload

    # Create a proper async context manager mock for the DBManager
    class MockAsyncContextManager:
        async def __aenter__(self):
            return MagicMock()  # Return a mock session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_db_manager_instance = MagicMock()
    mock_db_manager_instance.transaction.return_value = MockAsyncContextManager()

    with patch("ehp.core.services.token.SessionManager", return_value=mock_session_manager), \
         patch("ehp.db.DBManager", return_value=mock_db_manager_instance):

        auth_email_patch.start()
        auth_username_patch.start()

        # Step 3: Login with registered credentials
        login_data = {
            "username": "test@example.com",
            "password": "TestPassword123"
        }

        login_response = client.post("/token", json=login_data)

        assert login_response.status_code == 200
        login_response_data = login_response.json()
        assert login_response_data["access_token"] == "mock-token-12345"
        assert login_response_data["token_type"] == "bearer"
        assert "expires_at" in login_response_data
        
        auth_email_patch.stop()
        auth_username_patch.stop()
