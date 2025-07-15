from unittest.mock import patch

import pytest
from fastapi import HTTPException

from ehp.base.aws import AWSClient
from ehp.base.jwt_helper import JWT_SECRET_NAME, JWTGenerator
from ehp.base.session import SessionData
from ehp.config import settings
from ehp.utils.authentication import (
    check_password,
    hash_password,
    is_valid_token,
    needs_api_key,
    needs_token_auth,
)


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
class TestPasswordHashing:
    """Comprehensive test suite for password hashing functionality."""

    def test_hash_password_basic_functionality(self):
        """Test that hash_password creates a valid hash."""
        password = "testpassword"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert check_password(hashed, password)

    def test_hash_password_different_inputs_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password123"
        password2 = "different456"

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert hash1 != hash2
        assert check_password(hash1, password1)
        assert check_password(hash2, password2)
        assert not check_password(hash1, password2)
        assert not check_password(hash2, password1)

    def test_hash_password_same_input_different_salts(self):
        """Test that same password produces different hashes due to salt."""
        password = "samepassword"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Different salts should produce different hashes
        assert hash1 != hash2
        # But both should verify correctly
        assert check_password(hash1, password)
        assert check_password(hash2, password)

    def test_hash_password_complex_passwords(self):
        """Test hashing of complex passwords with special characters."""
        complex_passwords = [
            "P@ssw0rd!",
            "áéíóú123",
            "密码123",
            "password with spaces",
            "very_long_password_with_many_characters_12345",
            "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/`~",
        ]

        for password in complex_passwords:
            hashed = hash_password(password)
            assert hashed is not None
            assert hashed != password
            assert check_password(hashed, password)

    def test_hash_password_empty_input(self):
        """Test that hash_password raises exception with empty password."""
        with pytest.raises(Exception) as excinfo:
            hash_password("")

        assert "Password is required" in str(excinfo.value)

    def test_hash_password_none_input(self):
        """Test that hash_password raises exception with None password."""
        with pytest.raises(Exception) as excinfo:
            hash_password(None)

        assert "Password is required" in str(excinfo.value)

    def test_hash_password_whitespace_only(self):
        """Test that hash_password works with whitespace-only passwords."""
        whitespace_password = "   "
        hashed = hash_password(whitespace_password)

        assert hashed is not None
        assert check_password(hashed, whitespace_password)

    def test_hash_password_uses_scrypt_method(self):
        """Test that hash uses scrypt method as expected."""
        password = "testpassword"
        hashed = hash_password(password)

        # Scrypt hashes start with $scrypt$
        assert hashed.startswith("scrypt:")

    def test_check_password_correct_verification(self):
        """Test that check_password correctly validates passwords."""
        password = "testpassword"
        hashed = hash_password(password)

        assert check_password(hashed, password)
        assert not check_password(hashed, "wrongpassword")

    def test_check_password_case_sensitivity(self):
        """Test that password checking is case sensitive."""
        password = "TestPassword"
        hashed = hash_password(password)

        assert check_password(hashed, "TestPassword")
        assert not check_password(hashed, "testpassword")
        assert not check_password(hashed, "TESTPASSWORD")

    def test_check_password_edge_cases(self):
        """Test check_password with edge cases."""
        password = "validpassword"
        hashed = hash_password(password)

        # Empty strings
        assert not check_password(hashed, "")
        assert not check_password("", password)
        assert not check_password("", "")

        # None values
        assert not check_password(None, password)
        assert not check_password(hashed, None)
        assert not check_password(None, None)

        # Invalid hash format
        assert not check_password("invalid_hash", password)

    def test_check_password_similar_passwords(self):
        """Test that similar passwords are correctly differentiated."""
        base_password = "password123"
        similar_passwords = [
            "password124",
            "password123 ",
            " password123",
            "Password123",
            "password1234",
        ]

        hashed = hash_password(base_password)

        for similar_pwd in similar_passwords:
            assert not check_password(hashed, similar_pwd), (
                f"False positive for: {similar_pwd}"
            )

    def test_password_hashing_performance(self):
        """Test that password hashing completes in reasonable time."""
        import time

        password = "performance_test_password"

        start_time = time.time()
        hashed = hash_password(password)
        end_time = time.time()

        # Should complete within 1 second (scrypt is intentionally slow but not too slow)
        assert (end_time - start_time) < 1.0
        assert check_password(hashed, password)

    def test_hash_length_consistency(self):
        """Test that hashes have consistent length format."""
        passwords = [
            "short",
            "medium_length_password",
            "very_very_long_password_with_many_characters",
        ]

        hashes = [hash_password(pwd) for pwd in passwords]

        # All hashes should be strings and have reasonable length
        for hashed in hashes:
            assert isinstance(hashed, str)
            assert len(hashed) > 50  # Scrypt hashes are typically quite long
            assert len(hashed) < 200  # But not excessively long

    def test_registration_password_requirements_integration(self):
        """Test password hashing with registration schema requirements."""
        # These passwords meet registration schema requirements
        valid_registration_passwords = [
            "Password123",
            "SecurePass1",
            "MyStr0ngPassword",
            "ComplexP4ssword!",
        ]

        for password in valid_registration_passwords:
            hashed = hash_password(password)
            assert hashed is not None
            assert check_password(hashed, password)

            # Verify it doesn't match similar invalid passwords
            assert not check_password(hashed, password.lower())
            assert not check_password(hashed, password.upper())


@pytest.mark.unit
def test_is_valid_token(aws_mock: AWSClient):
    """Test that is_valid_token validates tokens correctly."""
    # Mock the get_from_redis_session function
    with (
        patch("ehp.base.session.SessionManager.get_session_from_token") as mock_get,
        patch("ehp.utils.authentication.log_error") as mock_log_error,
    ):
        # Valid token
        aws_mock.secretsmanager_client.create_secret(
            Name=JWT_SECRET_NAME, SecretString="test-secret"
        )
        jwt_generator = JWTGenerator()
        valid_token = jwt_generator.generate("test-user-id", "test@example.com")
        access_token = valid_token.access_token
        mock_get.return_value = SessionData(
            session_id="valid-session", session_token=access_token, metadata={}
        )
        assert is_valid_token(access_token)

        # Invalid token
        mock_get.return_value = None
        assert not is_valid_token("invalid-token")

        # Exception case
        exc = Exception("Redis error")
        mock_get.side_effect = exc
        assert not is_valid_token("error-token")
        mock_log_error.assert_called_once_with(exc)


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
