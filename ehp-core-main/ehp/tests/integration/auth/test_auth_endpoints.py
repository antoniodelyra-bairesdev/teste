import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI

from ehp.core.models.param import AuthenticationParam
from ehp.utils import constants as const
from ehp.utils.base import base64_encrypt
from ehp.utils.authentication import hash_password
from tests.utils.test_client import EHPTestClient
from tests.utils.mocks import mock_session_data


@pytest.mark.integration
def test_authenticate_success(app: FastAPI):
    """Test successful authentication."""
    client = EHPTestClient(app)

    # Setup mock authentication
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
    with patch("ehp.base.session.create_redis_session") as mock_create_session:
        # Set up the session token return value
        mock_create_session.return_value = "test-session-token"

        # Make the authentication request
        response = client.post(
            "/authenticate",
            json={
                "user_name": "testuser",
                "user_email": "test@example.com",
                "user_pwd": base64_encrypt("testpassword").decode("utf-8")
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        result = data["result"]

        # Check session token and user data
        assert "session_token" in result
        assert result["session_token"] == "test-session-token"
        assert result["id"] == user_data["id"]
        assert result["user_name"] == user_data["user_name"]

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()


@pytest.mark.integration
def test_authenticate_invalid_credentials(app: FastAPI):
    """Test authentication with invalid credentials."""
    client = EHPTestClient(app)

    # Setup mock authentication
    user_pwd_hash = hash_password("correctpassword")
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
            "language_id": 1
        }
    }

    auth_email_patch, auth_username_patch, mock_auth = client.setup_authentication(user_data)

    # Start patches
    auth_email_patch.start()
    auth_username_patch.start()

    # Make the authentication request with wrong password
    response = client.post(
        "/authenticate",
        json={
            "user_email": "test@example.com",
            "user_pwd": base64_encrypt("wrongpassword").decode("utf-8")
        }
    )

    # Verify response indicates error
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    result = data["result"]

    # Check error code and message
    assert result["CODE"] == const.ERROR_PASSWORD["CODE"]
    assert result["INFO"] == const.ERROR_PASSWORD["INFO"]

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()


@pytest.mark.integration
def test_authenticate_user_not_found(app: FastAPI):
    """Test authentication when user is not found."""
    client = EHPTestClient(app)

    # Setup mock authentication to return None (user not found)
    with patch("ehp.core.models.db.Authentication.get_by_email", return_value=None), \
            patch("ehp.core.models.db.Authentication.get_by_user_name", return_value=None):
        # Make the authentication request
        response = client.post(
            "/authenticate",
            json={
                "user_email": "nonexistent@example.com",
                "user_pwd": base64_encrypt("testpassword").decode("utf-8")
            }
        )

        # Verify response indicates user not found
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        result = data["result"]

        # Check error code and message
        assert result["CODE"] == const.ERROR_USER_DOES_NOT_EXIST["CODE"]
        assert result["INFO"] == const.ERROR_USER_DOES_NOT_EXIST["INFO"]


@pytest.mark.integration
def test_logout_success(app: FastAPI):
    """Test successful logout."""
    client = EHPTestClient(app)

    # Setup session mock
    session_data = mock_session_data()

    with patch("ehp.base.session.get_from_redis_session", return_value=session_data), \
            patch("ehp.base.session.remove_from_redis_session", return_value=None), \
            patch("ehp.core.services.authentication._auth_log", return_value=None):
        # Make logout request
        response = client.get("/logout", include_auth=True)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        result = data["result"]

        # Check success message
        assert "message" in result
        assert "Logged out successfully" in result["message"]


@pytest.mark.integration
def test_logout_unauthorized(app: FastAPI):
    """Test logout without auth token."""
    client = EHPTestClient(app)

    # Make logout request without auth token
    response = client.get("/logout", include_auth=False)

    # Verify response indicates unauthorized
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Invalid X-Token-Auth header" in response.json()["detail"]
