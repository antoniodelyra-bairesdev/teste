import pytest
from pydantic import ValidationError

from ehp.core.models.schema.registration import RegistrationSchema


@pytest.mark.unit
class TestRegistrationSchemaValidation:
    """Test suite for registration schema validation logic."""

    def test_valid_registration_data(self):
        """Test that valid registration data passes validation."""
        valid_data = {
            "user_name": "Rob Stuart",
            "user_email": "rob.stuart@wikiclip.com",
            "user_password": "SecurePa$s123"
        }
        registration = RegistrationSchema(**valid_data)
        
        assert registration.user_name == "Rob Stuart"
        assert registration.user_email == "rob.stuart@wikiclip.com"
        assert registration.user_password == "SecurePa$s123"

    def test_email_validation_success(self):
        """Test successful email validation cases."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk", 
            "user+tag@example-site.com",
            "123@numbers.org",
            "User@EXAMPLE.COM"  # Should be normalized to lowercase
        ]
        
        for email in valid_emails:
            data = {
                "user_name": "Test User",
                "user_email": email,
                "user_password": "ValidPa$s123"
            }
            registration = RegistrationSchema(**data)
            assert registration.user_email == email.lower()

    def test_email_validation_failures(self):
        """Test email validation failure cases."""
        invalid_emails = [
            "",
            "   ",
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user@com",
            "user@example."
        ]
        
        for email in invalid_emails:
            data = {
                "user_name": "Test User",
                "user_email": email,
                "user_password": "ValidPa$s123"
            }
            with pytest.raises(ValidationError) as exc_info:
                RegistrationSchema(**data)
            
            errors = exc_info.value.errors()
            assert any("email" in str(error).lower() for error in errors)

    def test_email_normalization(self):
        """Test that email is properly normalized."""
        data = {
            "user_name": "Test User",
            "user_email": "  USER@EXAMPLE.COM  ",
            "user_password": "ValidPa$s123"
        }
        registration = RegistrationSchema(**data)
        assert registration.user_email == "user@example.com"

    def test_name_validation_success(self):
        """Test successful name validation cases."""
        valid_names = [
            "Rob Stuart",
            "Rob",
            "Md. Rob Stuart",
            "María García",
            "李小明",
        ]
        
        for name in valid_names:
            data = {
                "user_name": name,
                "user_email": "test@example.com",
                "user_password": "ValidPa$s123"
            }
            registration = RegistrationSchema(**data)
            assert registration.user_name == name.strip()

    def test_name_validation_failures(self):
        """Test name validation failure cases."""
        invalid_names = [
            "",
            "   ",
            "  \t\n  "
        ]
        
        for name in invalid_names:
            data = {
                "user_name": name,
                "user_email": "test@example.com",
                "user_password": "ValidPa$s123"
            }
            with pytest.raises(ValidationError) as exc_info:
                RegistrationSchema(**data)
            
            errors = exc_info.value.errors()
            assert any("name" in str(error).lower() for error in errors)

    def test_name_whitespace_trimming(self):
        """Test that name whitespace is properly trimmed."""
        data = {
            "user_name": "  Rob Stuart  ",
            "user_email": "test@example.com",
            "user_password": "ValidPa$s123"
        }
        registration = RegistrationSchema(**data)
        assert registration.user_name == "Rob Stuart"

    def test_password_validation_success(self):
        """Test successful password validation cases."""
        valid_passwords = [
            "Pa$sword123",
            "SecurePa$s1",
            "MyStr0ngP@ssw0rd",
            "Aa12345678!",
            "ComplexP4ssword!"
        ]
        
        for password in valid_passwords:
            data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": password
            }
            registration = RegistrationSchema(**data)
            assert registration.user_password == password

    def test_password_minimum_length_failure(self):
        """Test password minimum length validation."""
        short_passwords = [
            "",
            "Pass1",
            "Aa1",
            "1234567"  # 7 characters
        ]
        
        for password in short_passwords:
            data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": password
            }
            with pytest.raises(ValidationError) as exc_info:
                RegistrationSchema(**data)
            
            errors = exc_info.value.errors()
            assert any("8 characters" in str(error) for error in errors)

    def test_password_uppercase_requirement_failure(self):
        """Test password uppercase letter requirement."""
        no_uppercase_passwords = [
            "password123",
            "lowercase1",
            "alllower8chars"
        ]
        
        for password in no_uppercase_passwords:
            data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": password
            }
            with pytest.raises(ValidationError) as exc_info:
                RegistrationSchema(**data)
            
            errors = exc_info.value.errors()
            assert any("uppercase" in str(error).lower() for error in errors)

    def test_password_lowercase_requirement_failure(self):
        """Test password lowercase letter requirement."""
        no_lowercase_passwords = [
            "PASSWORD123",
            "UPPERCASE1",
            "ALLUPPER8CHARS"
        ]
        
        for password in no_lowercase_passwords:
            data = {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "user_password": password
            }
            with pytest.raises(ValidationError) as exc_info:
                RegistrationSchema(**data)
            
            errors = exc_info.value.errors()
            assert any("lowercase" in str(error).lower() for error in errors)

    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are captured."""
        invalid_data = {
            "user_name": "",
            "user_email": "invalid-email",
            "user_password": "weak"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            RegistrationSchema(**invalid_data)
        
        errors = exc_info.value.errors()
        assert len(errors) >= 3  # Should have at least 3 validation errors
        
        error_messages = [str(error) for error in errors]
        assert any("name" in msg.lower() for msg in error_messages)
        assert any("email" in msg.lower() for msg in error_messages)
        assert any("password" in msg.lower() for msg in error_messages)
