import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call

from ehp.core.models.db.authentication import Authentication
from ehp.tests.utils.test_client import EHPTestClient


@pytest.mark.integration
class TestRegistrationEndpoints:
    """Integration tests for Registration API endpoints."""

    @pytest.fixture
    def valid_registration_data(self):
        """Valid registration data for testing."""
        return {
            "user_name": "Test User",
            "user_email": "test@example.com",
            "user_password": "SecurePa$s123"
        }

    class TestRegisterEndpoint:
        """Test the /register endpoint."""

        async def test_register_success(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test successful user registration."""
            with patch('ehp.core.services.registration.log_info'):
                response = test_client.post("/register", json=valid_registration_data)

            assert response.status_code == 200
            response_data = response.json()

            assert "result" in response_data
            assert "pagination" in response_data
            assert "metadata" in response_data

            assert response_data["metadata"]["status_code"] == 200
            assert "response_id" in response_data["metadata"]
            assert "response_time" in response_data["metadata"]

            assert "code" in response_data["result"]
            assert "message" in response_data["result"]
            assert "auth" in response_data["result"]
            assert "user" in response_data["result"]

            assert response_data["result"]["code"] == 200
            assert "successfully" in response_data["result"]["message"].lower()

            auth_data = response_data["result"]["auth"]
            assert "user_email" in auth_data
            assert "user_name" in auth_data
            assert "id" in auth_data
            assert "is_active" in auth_data
            assert "is_confirmed" in auth_data
            assert "profile_id" in auth_data
            assert "created_at" in auth_data

            user_data = response_data["result"]["user"]
            assert "full_name" in user_data
            assert "id" in user_data
            assert "auth_id" in user_data
            assert "created_at" in user_data

            assert auth_data["user_email"] == valid_registration_data["user_email"]
            assert user_data["full_name"] == valid_registration_data["user_name"]
            assert "user_pwd" not in auth_data

        async def test_register_email_already_exists(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test registration with email that already exists."""
            with patch('ehp.core.services.registration.AuthenticationRepository') as mock_auth_repo:
                with patch('ehp.core.services.registration.log_info'):
                    mock_repo_instance = AsyncMock()
                    mock_auth_repo.return_value = mock_repo_instance
                    existing_auth = Authentication(
                        id=999,
                        user_email="test@example.com",
                        user_name="test@example.com"
                    )
                    mock_repo_instance.get_by_email.return_value = existing_auth
                    response = test_client.post("/register", json=valid_registration_data)

            assert response.status_code == 422
            response_data = response.json()
            assert "error" in response_data
            assert "already exists" in response_data["error"]

        async def test_register_validation_error_password_too_short(
            self, test_client: EHPTestClient
        ):
            """Test registration with password that's too short."""
            invalid_data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": "short"
            }
            response = test_client.post("/register", json=invalid_data)
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "Password must be at least 8 characters" in d["msg"]
                for d in response_data["detail"]
            )

        async def test_register_validation_error_password_no_uppercase(
            self, test_client: EHPTestClient
        ):
            """Test registration with password missing uppercase letter."""
            invalid_data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": "lowercase123"
            }
            response = test_client.post("/register", json=invalid_data)
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "uppercase" in d["msg"].lower() for d in response_data["detail"]
            )

        async def test_register_validation_error_password_no_lowercase(
            self, test_client: EHPTestClient
        ):
            """Test registration with password missing lowercase letter."""
            invalid_data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": "UPPERCASE123"
            }
            response = test_client.post("/register", json=invalid_data)
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "lowercase" in d["msg"].lower() for d in response_data["detail"]
            )

        async def test_register_validation_error_invalid_email(
            self, test_client: EHPTestClient
        ):
            """Test registration with invalid email format."""
            invalid_data = {
                "user_name": "Test User",
                "user_email": "invalid-email",
                "user_password": "SecurePass123"
            }
            response = test_client.post("/register", json=invalid_data)
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "email" in d["msg"].lower() for d in response_data["detail"]
            )

        async def test_register_validation_error_missing_name(
            self, test_client: EHPTestClient
        ):
            """Test registration with missing name."""
            invalid_data = {
                "user_name": "",
                "user_email": "test@example.com",
                "user_password": "SecurePass123"
            }
            response = test_client.post("/register", json=invalid_data)
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "name is required" in d["msg"].lower() for d in response_data["detail"]
            )

        async def test_register_validation_error_generic(
            self, test_client: EHPTestClient
        ):
            """Test registration with generic validation error."""
            invalid_data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": "SecurePa$s123"
            }
            response = test_client.post("/register", json=invalid_data)
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data

    class TestRegistrationWithProfileEndpoint:
        """Test the /registration/{profile_code} endpoint."""

        async def test_registration_with_profile_success(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test registration with profile code."""
            profile_code = "user"
            response = test_client.post(
                f"/registration/{profile_code}",
                json=valid_registration_data
            )
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data
            assert "pagination" in response_data
            assert "metadata" in response_data
            assert response_data["metadata"]["status_code"] == 200
            assert "response_id" in response_data["metadata"]
            assert "response_time" in response_data["metadata"]
            assert response_data["result"] == {}

        async def test_registration_with_profile_database_error(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            profile_code = "user"
            with patch('ehp.core.services.registration.ManagedAsyncSession') as mock_session:
                mock_session.side_effect = Exception("Database error")
                response = test_client.post(
                    f"/registration/{profile_code}",
                    json=valid_registration_data
                )
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data
            assert response_data["result"] == {}

        async def test_registration_with_profile_rollback(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            profile_code = "user"
            with patch('ehp.core.services.registration.ManagedAsyncSession') as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.__aenter__.side_effect = Exception(
                    "Transaction error"
                )
                response = test_client.post(
                    f"/registration/{profile_code}",
                    json=valid_registration_data
                )
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data
            assert response_data["result"] == {}

        async def test_registration_with_profile_logs_error(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            profile_code = "user"
            with patch('ehp.core.services.registration.ManagedAsyncSession') as mock_session:
                mock_session.side_effect = Exception("Database error")
                with patch('ehp.core.services.registration.log_error'):
                    response = test_client.post(
                        f"/registration/{profile_code}",
                        json=valid_registration_data
                    )
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data
            assert response_data["result"] == {}

    class TestRegistrationLogging:
        """Test logging behavior in registration endpoints."""

        async def test_register_logs_info_messages(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            with patch('ehp.core.services.registration.log_info'):
                response = test_client.post("/register", json=valid_registration_data)
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data
            assert "metadata" in response_data
            assert "code" in response_data["result"]
            assert "auth" in response_data["result"]
            assert "user" in response_data["result"]

        async def test_register_logs_error_on_exception(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            with patch('ehp.core.services.registration.AuthenticationRepository') as mock_auth_repo:
                mock_repo_instance = AsyncMock()
                mock_auth_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_email.side_effect = Exception("Database error")
                with patch('ehp.core.services.registration.log_error'):
                    response = test_client.post("/register", json=valid_registration_data)
            assert response.status_code == 200
            response_data = response.json()
            assert "result" in response_data
            assert response_data["result"]["CODE"] == 500

    class TestRegistrationConfirmationEmail:
        """Test confirmation email functionality in registration."""
        
        async def test_register_sends_confirmation_email(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test that registration sends a confirmation email with correct token."""
            with patch('ehp.core.services.registration.log_info'):
                with patch('ehp.core.services.registration.UserMailer') as mock_mailer_class:
                    # Create a mock mailer instance
                    mock_mailer = AsyncMock()
                    mock_mailer.send_mail = AsyncMock(return_value=True)
                    mock_mailer_class.return_value = mock_mailer
                    
                    # Make the registration request
                    response = test_client.post("/register", json=valid_registration_data)
                    
                    # Verify successful registration
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["result"]["code"] == 200
                    
                    # Verify UserMailer was instantiated
                    mock_mailer_class.assert_called_once()
                    
                    # Verify send_mail was called
                    mock_mailer.send_mail.assert_called_once()
                    
                    # Extract the call arguments
                    call_args = mock_mailer.send_mail.call_args
                    subject = call_args[0][0]
                    body = call_args[0][1]
                    recipients = call_args[0][2]
                    
                    # Verify email details
                    assert subject == "Welcome! Please Confirm Your Email"
                    assert valid_registration_data["user_email"] in recipients
                    assert "https://example.com/confirm-email?token=" in body
                    assert "Welcome to Wikiclip!" in body
                    assert "expire in 30 days" in body
                    
                    # Extract token from body and verify it's a valid hex token
                    import re
                    token_match = re.search(r'token=([a-f0-9]{64})', body)
                    assert token_match, "Should find a 64-character hex token in email body"
                    
                    # Verify force and include_self parameters
                    assert call_args[1]["force"] is True
                    assert call_args[1]["include_self"] is False
        
        async def test_register_email_failure_does_not_fail_registration(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test that registration succeeds even if confirmation email fails to send."""
            with patch('ehp.core.services.registration.log_info'):
                with patch('ehp.core.services.registration.log_error') as mock_log_error:
                    with patch('ehp.core.services.registration.UserMailer') as mock_mailer_class:
                        # Create a mock mailer that fails to send
                        mock_mailer = AsyncMock()
                        mock_mailer.send_mail = AsyncMock(return_value=False)
                        mock_mailer_class.return_value = mock_mailer
                        
                        # Make the registration request
                        response = test_client.post("/register", json=valid_registration_data)
                        
                        # Verify registration still succeeds
                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["result"]["code"] == 200
                        assert "successfully" in response_data["result"]["message"].lower()
                        
                        # Verify error was logged
                        mock_log_error.assert_called()
                        error_msg = str(mock_log_error.call_args[0][0])
                        assert "Failed to send confirmation email" in error_msg
        
        async def test_register_email_exception_does_not_fail_registration(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test that registration succeeds even if email sending raises an exception."""
            with patch('ehp.core.services.registration.log_info'):
                with patch('ehp.core.services.registration.log_error') as mock_log_error:
                    with patch('ehp.core.services.registration.UserMailer') as mock_mailer_class:
                        # Create a mock mailer that raises an exception
                        mock_mailer = AsyncMock()
                        mock_mailer.send_mail = AsyncMock(side_effect=Exception("SMTP error"))
                        mock_mailer_class.return_value = mock_mailer
                        
                        # Make the registration request
                        response = test_client.post("/register", json=valid_registration_data)
                        
                        # Verify registration still succeeds
                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["result"]["code"] == 200
                        
                        # Verify error was logged
                        mock_log_error.assert_called()
                        error_msg = str(mock_log_error.call_args[0][0])
                        assert "Error sending confirmation email" in error_msg
        
        async def test_register_stores_confirmation_token_in_database(
            self, test_client: EHPTestClient, valid_registration_data: dict
        ):
            """Test that confirmation token is stored in the database."""
            with patch('ehp.core.services.registration.log_info'):
                with patch('ehp.core.services.registration.UserMailer'):
                    # Make the registration request
                    response = test_client.post("/register", json=valid_registration_data)
                    
                    # Verify successful registration
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["result"]["code"] == 200
                    
                    # Verify token is not exposed in response
                    auth_data = response_data["result"]["auth"]
                    assert "confirmation_token" not in auth_data
                    assert "confirmation_token_expires" not in auth_data
