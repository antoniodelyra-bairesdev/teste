import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

from ehp.utils.authentication import (
    needs_api_key,
    needs_token_auth,
    hash_password,
    check_password,
    is_valid_token
)
from ehp.config import settings


@pytest.mark.unit
def test_needs_api_key_valid():
    """Test that needs_api_key passes with valid key."""
    # This should not raise an exception
    assert needs_api_key(settings.API_KEY_VALUE) is None


@pytest.mark.unit
def test_needs_api_key_invalid():
    """Test that needs_api_key raises exception with invalid key."""
    with pytest.raises(HTTPException) as excinfo:
        needs_api_key("invalid-key")

    assert excinfo.value.status_code == 400
    assert "Invalid X-Api-Key header" in excinfo.value.detail


@pytest.mark.unit
def test_needs_api_key_missing():
    """Test that needs_api_key raises exception with missing key."""
    with pytest.raises(HTTPException) as excinfo:
        needs_api_key(None)

    assert excinfo.value.status_code == 400
    assert "Invalid X-Api-Key header" in excinfo.value.detail


@pytest.mark.unit
def test_hash_password():
    """Test that hash_password creates a valid hash."""
    password = "testpassword"
    hashed = hash_password(password)

    assert hashed is not None
    assert hashed != password
    assert check_password(hashed, password)


@pytest.mark.unit
def test_hash_password_empty():
    """Test that hash_password raises exception with empty password."""
    with pytest.raises(Exception) as excinfo:
        hash_password("")

    assert "Password is required" in str(excinfo.value)


@pytest.mark.unit
def test_check_password():
    """Test that check_password correctly validates passwords."""
    password = "testpassword"
    hashed = hash_password(password)

    assert check_password(hashed, password)
    assert not check_password(hashed, "wrongpassword")
    assert not check_password(hashed, "")
    assert not check_password("", password)
    assert not check_password(None, password)
    assert not check_password(hashed, None)


@pytest.mark.unit
def test_is_valid_token():
    """Test that is_valid_token validates tokens correctly."""
    # Mock the get_from_redis_session function
    with patch("ehp.utils.authentication.get_from_redis_session") as mock_get:
        # Valid token
        mock_get.return_value = {"session_id": "test-session", "session_info": {}}
        assert is_valid_token("valid-token")

        # Invalid token
        mock_get.return_value = None
        assert not is_valid_token("invalid-token")

        # Exception case
        mock_get.side_effect = Exception("Redis error")
        assert not is_valid_token("error-token")


@pytest.mark.unit
async def test_needs_token_auth():
    """Test that needs_token_auth validates auth tokens correctly."""
    # Mock is_valid_token
    with patch("ehp.utils.authentication.is_valid_token") as mock_valid:
        # Valid token
        mock_valid.return_value = True
        assert await needs_token_auth("valid-token") is None

        # Invalid token
        mock_valid.return_value = False
        with pytest.raises(HTTPException) as excinfo:
            await needs_token_auth("invalid-token")

        assert excinfo.value.status_code == 400
        assert "Invalid X-Token-Auth header" in excinfo.value.detail

        # Missing token
        with pytest.raises(HTTPException) as excinfo:
            await needs_token_auth(None)

        assert excinfo.value.status_code == 400
        assert "Invalid X-Token-Auth header" in excinfo.value.detail
