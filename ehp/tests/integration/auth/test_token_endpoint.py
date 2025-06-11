from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ehp.base.jwt_helper import TokenPayload
from ehp.config.ehp_core import settings
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.schema.token import TokenRequestData
from ehp.utils.authentication import hash_password


# Mock user data base
@pytest.fixture
def valid_user() -> Authentication:
    return Authentication(
        **{
            "id": 123,
            "user_name": "mockuser",
            "user_email": "mock@example.com",
            "user_pwd": hash_password(
                "hashedpassword"
            ),  # Simulating a pre-hashed password
            "is_active": "1",
            "is_confirmed": "1",
            "retry_count": 0,
        }
    )


@pytest.mark.integration
@patch(
    "ehp.core.repositories.AuthenticationRepository.get_by_email",
)
@patch(
    "ehp.core.repositories.AuthenticationRepository.get_by_username",
)
@patch("ehp.base.session.SessionManager.create_session")
@pytest.mark.usefixtures("setup_jwt")
def test_account_lockout(
    mock_create_session,
    mock_get_by_email,
    mock_get_by_username,
    valid_user: Authentication,
    test_client: TestClient,
):
    # Mock session creation
    mock_create_session.return_value = {
        "access_token": "mocked_token_value",
        "refresh_token": "mocked_refresh_token",
        "token_type": "bearer",
        "expires_at": 3600,
    }
    mock_get_by_email.return_value = valid_user
    mock_get_by_username.return_value = valid_user

    # Create token request data for the test
    token_request_data = TokenRequestData(
        username=valid_user.user_email, password="hashedpassword"
    )

    # Call the /token endpoint using EHPTestClient
    response = test_client.post(
        "/token", json=token_request_data.model_dump(mode="json")
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "mocked_token_value"
    assert data["token_type"] == "bearer"
    assert data["expires_at"] == 3600


@pytest.mark.integration
def test_token_missing_fields(test_client: TestClient):
    """Test when username or password is missing"""
    response = test_client.post("/token", json={})
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.integration
@patch("ehp.base.session.SessionManager.create_session")
@pytest.mark.usefixtures("setup_jwt")
def test_token_invalid_credentials(mock_create_session, test_client):
    """Test invalid credentials (wrong username or password)"""
    mock_create_session.return_value = None  # Simulate a failed token generation

    response = test_client.post(
        "/token",
        json={"username": "wronguser@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
@patch("ehp.core.repositories.AuthenticationRepository.get_by_email")
@patch("ehp.base.session.SessionManager.create_session")
@pytest.mark.usefixtures("setup_jwt")
def test_token_deactivated_account(
    mock_create_session,
    mock_get_by_email,
    test_client: TestClient,
    valid_user: Authentication,
):
    """Test when the account is deactivated"""

    valid_user.is_active = "0"  # Deactivate user
    mock_get_by_email.return_value = valid_user
    mock_create_session.return_value = TokenPayload(
        access_token="mocked_token_value",
        refresh_token="mocked_refresh_token",
        token_type="bearer",
        expires_at=3600,
    )

    response = test_client.post(
        "/token",
        json={"username": valid_user.user_email, "password": "hashedpassword"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Account is deactivated"


@pytest.mark.integration
@patch("ehp.core.repositories.AuthenticationRepository.get_by_email")
@patch("ehp.base.session.SessionManager.create_session")
def test_token_not_confirmed_account(
    mock_create_session,
    mock_get_by_email,
    test_client: TestClient,
    valid_user: Authentication,
):
    """Test when the account is not confirmed"""
    valid_user.is_confirmed = "0"  # Unconfirmed user
    mock_get_by_email.return_value = valid_user
    mock_create_session.return_value = TokenPayload(
        access_token="mocked_token_value",
        refresh_token="mocked_refresh_token",
        token_type="bearer",
        expires_at=3600,
    )

    response = test_client.post(
        "/token",
        json={"username": valid_user.user_email, "password": "hashedpassword"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Account is not confirmed"


@pytest.mark.integration
@patch(
    "ehp.core.repositories.AuthenticationRepository.get_by_email",
)
@patch(
    "ehp.core.repositories.AuthenticationRepository.get_by_username",
)
@patch("ehp.base.session.SessionManager.create_session")
@pytest.mark.usefixtures("setup_jwt")
def test_account_lockout(
    mock_create_session,
    mock_get_by_email,
    mock_get_by_username,
    valid_user: Authentication,
    test_client: TestClient,
):
    # Mock session creation
    mock_create_session.return_value = {
        "access_token": "mocked_token_value",
        "refresh_token": "mocked_refresh_token",
        "token_type": "bearer",
        "expires_at": 3600,
    }
    mock_get_by_email.return_value = valid_user
    mock_get_by_username.return_value = valid_user

    # Create token request data for the test
    token_request_data = TokenRequestData(
        username=valid_user.user_email, password="invalidpassword"
    )

    # Call the /token endpoint using EHPTestClient
    for idx in range(settings.LOGIN_ERROR_MAX_RETRY):
        response = test_client.post(
            "/token", json=token_request_data.model_dump(mode="json")
        )
        data = response.json()
        detail = data.get("detail", {})
        assert response.status_code == 401
        assert detail["detail"] == "Invalid credentials"
        assert detail["retry_count"] == idx + 1
        assert detail["left_attempts"] == settings.LOGIN_ERROR_MAX_RETRY - (idx + 1)

    # After max retries, the account should be locked
    response = test_client.post(
        "/token", json=token_request_data.model_dump(mode="json")
    )
    assert response.status_code == 423
    data = response.json()
    detail = data.get("detail", {})
    assert detail["detail"] == "Account locked due to too many failed login attempts"
    assert detail["retry_count"] == settings.LOGIN_ERROR_MAX_RETRY
    assert (
        0 < detail["wait_time"] <= settings.LOGIN_ERROR_TIMEOUT
    )  # Ensure wait time is within expected range


@pytest.mark.integration
@patch(
    "ehp.core.repositories.AuthenticationRepository.get_by_email",
)
@patch(
    "ehp.core.repositories.AuthenticationRepository.get_by_username",
)
@patch("ehp.base.session.SessionManager.create_session")
@pytest.mark.usefixtures("setup_jwt")
def test_account_lockout_resets_after_timeout(
    mock_create_session,
    mock_get_by_email,
    mock_get_by_username,
    valid_user: Authentication,
    test_client: TestClient,
):
    # Mock session creation
    mock_create_session.return_value = TokenPayload(
        access_token="mocked_token_value",
        refresh_token="mocked_refresh_token",
        token_type="bearer",
        expires_at=3600,
    )
    mock_get_by_email.return_value = valid_user
    mock_get_by_username.return_value = valid_user

    # Create token request data for the test
    token_request_data = TokenRequestData(
        username=valid_user.user_email, password="invalidpassword"
    )

    # Call the /token endpoint using EHPTestClient
    for idx in range(settings.LOGIN_ERROR_MAX_RETRY):
        response = test_client.post(
            "/token", json=token_request_data.model_dump(mode="json")
        )
        data = response.json()
        detail = data.get("detail", {})
        assert response.status_code == 401
        assert detail["detail"] == "Invalid credentials"
        assert detail["retry_count"] == idx + 1
        assert detail["left_attempts"] == settings.LOGIN_ERROR_MAX_RETRY - (idx + 1)

    # After max retries, the account should be locked
    response = test_client.post(
        "/token", json=token_request_data.model_dump(mode="json")
    )
    assert response.status_code == 423
    assert (
        response.json()["detail"]["detail"]
        == "Account locked due to too many failed login attempts"
    )

    # unlock account by simulating timeout
    valid_user.last_login_attempt = valid_user.last_login_attempt - timedelta(
        seconds=settings.LOGIN_ERROR_TIMEOUT
    )

    response = test_client.post(
        "/token",
        json={"username": valid_user.user_email, "password": "hashedpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "mocked_token_value"
