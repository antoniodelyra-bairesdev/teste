from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette import status

from ehp.base.jwt_helper import TokenPayload
from ehp.core.models.db.authentication import Authentication
from ehp.core.services.logout import router as logout_router
from ehp.core.services.token import router as token_router
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password

# Set up FastAPI app with the /token and /logout endpoints
app = FastAPI()
app.include_router(token_router)
app.include_router(logout_router)



@pytest.mark.integration
@patch("ehp.core.repositories.authentication.AuthenticationRepository.get_by_email")
@patch("ehp.core.repositories.authentication.AuthenticationRepository.get_by_username")
@patch("ehp.base.session.SessionManager.create_session")
@patch("ehp.base.session.SessionManager.remove_session_from_token")
@pytest.mark.usefixtures("setup_jwt")
def test_logout_flow(
    mock_remove_session,
    mock_create_session,
    mock_get_by_username,
    mock_get_by_email,
    test_client: EHPTestClient, 
):
    # Mock user data
    valid_user = Authentication(
        id=123,
        user_name="mockuser",
        user_email="mock@example.com",
        user_pwd=hash_password("validpassword"),
        is_active="1",
        is_confirmed="1",
        retry_count=0,
    )
    mock_get_by_email.return_value = valid_user
    mock_get_by_username.return_value = valid_user

    # Mock session creation to simulate a login
    mock_create_session.return_value = TokenPayload(
        access_token="mocked_token_value",
        refresh_token=None,
        token_type="bearer",
        expires_at=3600,
    )

    # 1. Login to get a token
    login_response = test_client.post(
        "/token", json={"username": "mock@example.com", "password": "validpassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # 2. Logout with the token
    logout_response = test_client.post("/logout", headers={"x-token-auth": token})

    # 3. Verify the response and that the session was removed
    assert logout_response.status_code == 200
    assert logout_response.json() == {
        "message": "Logged out successfully",
        "status_code": status.HTTP_200_OK,
    }
    mock_remove_session.assert_called_once_with(token)
