import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI

from ehp.base.session import create_redis_session
from ehp.utils.base import base64_encrypt
from ehp.utils.authentication import hash_password
from tests.utils.test_client import EHPTestClient


@pytest.mark.end_to_end
def test_auth_and_logout_flow(app: FastAPI):
    """
    Test a complete authentication flow:
    1. User authenticates
    2. User accesses a protected endpoint
    3. User logs out
    4. User is denied access to protected endpoint
    """
    client = EHPTestClient(app)

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
            "students": []
        }
    }

    auth_email_patch, auth_username_patch, mock_auth = client.setup_authentication(user_data)

    # Start patches
    auth_email_patch.start()
    auth_username_patch.start()

    # Setup session creation mock
    session_token = "test-session-token"

    with patch("ehp.base.session.create_redis_session", return_value=session_token), \
            patch("ehp.base.session.get_from_redis_session") as mock_get_session, \
            patch("ehp.base.session.remove_from_redis_session") as mock_remove_session, \
            patch("ehp.core.services.authentication._auth_log", return_value=None):
        # Configure mock_get_session to simulate valid session initially
        mock_get_session.return_value = {
            "session_id": "test-session-id",
            "session_info": user_data
        }

        # Step 1: User authenticates
        login_response = client.post(
            "/authenticate",
            json={
                "user_name": "testuser",
                "user_email": "test@example.com",
                "user_pwd": base64_encrypt("testpassword").decode("utf-8")
            }
        )

        assert login_response.status_code == 200
        assert login_response.json()["result"]["session_token"] == session_token

        # Save the token for later requests
        client.auth_token = session_token

        # Step 2: User accesses a protected endpoint
        protected_response = client.get("/_meta", include_auth=True)
        assert protected_response.status_code == 200

        # Step 3: User logs out
        logout_response = client.get("/logout", include_auth=True)
        assert logout_response.status_code == 200
        assert "Logged out successfully" in logout_response.json()["result"]["message"]

        # Verify remove_from_redis_session was called with the session token
        mock_remove_session.assert_called_with(session_token)

        # Step 4: Configure mock to simulate invalid session after logout
        mock_get_session.return_value = None

        # User is denied access to protected endpoint
        protected_response = client.get("/_meta", include_auth=True)
        assert protected_response.status_code == 400
        assert "Invalid X-Token-Auth header" in protected_response.json()["detail"]

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()


@pytest.mark.end_to_end
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
        "person": {
            "id": 1,
            "language_id": 1
        }
    }

    auth_email_patch, auth_username_patch, mock_auth = client.setup_authentication(user_data)

    # Start patches
    auth_email_patch.start()
    auth_username_patch.start()

    with patch("ehp.utils.email.send_notification", return_value=True):
        # Step 1: User requests password reset
        reset_response = client.post(
            "/user/pwd",
            json={
                "auth_id": 1,
                "user_email": "test@example.com"
            }
        )

        assert reset_response.status_code == 200
        assert reset_response.json()["result"]["CODE"] == 200

        # Verify that reset code was generated and set
        assert mock_auth.reset_password == "1"
        assert mock_auth.reset_code is not None

        reset_code = mock_auth.reset_code

        # Step 2: User validates reset code
        validate_response = client.put(
            "/user/validate/code",
            json={
                "auth_id": 1,
                "reset_code": reset_code
            }
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
                "user_password": base64_encrypt(new_password).decode("utf-8")
            }
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
