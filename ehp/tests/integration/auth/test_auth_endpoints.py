from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from ehp.config.ehp_core import settings
from ehp.tests.utils.mocks import mock_session_data
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password, is_valid_token


@pytest.mark.integration
@pytest.mark.usefixtures("setup_jwt")
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
            "students": [],
        },
    }

    auth_email_patch, auth_username_patch, mock_auth = client.setup_authentication(
        user_data
    )

    # Start patches
    auth_email_patch.start()
    auth_username_patch.start()

    # Setup session creation mock

    # Make the authentication request
    response = client.post(
        "/token",
        json={
            "username": "testuser",
            "password": "testpassword",
        },
    )

    # Verify response
    assert response.status_code == 200
    result = response.json()

    # Check session token and user data
    assert "access_token" in result
    assert is_valid_token(result["access_token"])

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()


@pytest.mark.integration
def test_authenticate_invalid_credentials(test_client: EHPTestClient):
    """Test authentication with invalid credentials."""

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
            "language_id": 1,
        },
    }

    auth_email_patch, auth_username_patch, mock_auth = test_client.setup_authentication(
        user_data
    )

    # Start patches
    auth_email_patch.start()
    auth_username_patch.start()

    # Make the authentication request with wrong password
    response = test_client.post(
        "/token",
        json={
            "username": "test@example.com",
            "password": "wrongpassword",
        },
    )

    # Verify response indicates error
    assert response.status_code == 401
    result = response.json()
    detail: dict[str, Any] = result["detail"]

    # Check error code and message
    assert detail["detail"] == "Invalid credentials"
    assert detail["retry_count"] == 1
    assert detail["left_attempts"] == settings.LOGIN_ERROR_MAX_RETRY - 1

    # Stop patches
    auth_email_patch.stop()
    auth_username_patch.stop()


@pytest.mark.integration
def test_authenticate_user_not_found(app: FastAPI):
    """Test authentication when user is not found."""
    client = EHPTestClient(app)

    # Setup mock authentication to return None (user not found)
    with patch(
        "ehp.core.repositories.AuthenticationRepository.get_by_email", return_value=None
    ), patch(
        "ehp.core.repositories.AuthenticationRepository.get_by_username",
        return_value=None,
    ):
        # Make the authentication request
        response = client.post(
            "/token",
            json={"username": "nonexistent@example.com", "password": "testpassword"},
        )

        # Verify response indicates user not found
        assert response.status_code == 401
        result = response.json()

        # Check error code and message
        assert result["detail"] == "Invalid credentials"


@pytest.mark.integration
@pytest.mark.skip(reason="Logout functionality is not implemented yet")
def test_logout_success(app: FastAPI):
    """Test successful logout."""
    client = EHPTestClient(app)

    # Setup session mock
    session_data = mock_session_data()

    with patch(
        "ehp.base.session.SessionManager.create_session", return_value=session_data
    ), patch("ehp.base.session.SessionManager.remove_session", return_value=None):
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
@pytest.mark.skip(reason="Logout functionality is not implemented yet")
def test_logout_unauthorized(app: FastAPI):
    """Test logout without auth token."""
    client = EHPTestClient(app)

    # Make logout request without auth token
    response = client.get("/logout", include_auth=False)

    # Verify response indicates unauthorized
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Invalid X-Token-Auth header" in response.json()["detail"]
