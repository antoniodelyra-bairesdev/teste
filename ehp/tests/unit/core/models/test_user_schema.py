import pytest
from pydantic import ValidationError

from ehp.core.models.schema.user import (
    UserDisplayNameResponseSchema,
    UserDisplayNameUpdateSchema,
)
from ehp.utils.constants import (
    DISPLAY_NAME_MAX_LENGTH,
    DISPLAY_NAME_MIN_LENGTH,
)


@pytest.mark.unit
class TestUserDisplayNameUpdateSchema:
    """Test suite for UserDisplayNameUpdateSchema validation logic."""

    def test_valid_display_name(self):
        """Test that valid display names pass validation."""
        valid_names = [
            "JohnDoe",
            "AliceSmith",
            "JoãoSilva",
            "MaríaGarcía",
            "test_user",
            "user-name",
            "User123",
            "AB",  # minimum 2 characters
            "user123",
            "test-user",
            "user_name",
            "João123",
            "user.name",  # With dot
            "test.user.name",  # Multiple dots
            "user123.name",  # Numbers and dots
        ]

        for name in valid_names:
            schema = UserDisplayNameUpdateSchema(display_name=name)
            assert schema.display_name == name.strip()

    def test_display_name_required(self):
        """Test that display name is required."""
        with pytest.raises(ValidationError) as exc_info:
            UserDisplayNameUpdateSchema(display_name="")

        errors = exc_info.value.errors()
        assert any("Display name is required" in str(error) for error in errors)

    def test_display_name_whitespace_only(self):
        """Test that whitespace-only display names are rejected."""
        whitespace_names = ["   ", "\t\t", "\n\n", "  \t  \n  "]

        for name in whitespace_names:
            with pytest.raises(ValidationError) as exc_info:
                UserDisplayNameUpdateSchema(display_name=name)

            errors = exc_info.value.errors()
            assert any("Display name is required" in str(error) for error in errors)

    def test_display_name_minimum_length(self):
        """Test minimum length validation."""
        short_name = "A" * (DISPLAY_NAME_MIN_LENGTH - 1)

        with pytest.raises(ValidationError) as exc_info:
            UserDisplayNameUpdateSchema(display_name=short_name)

        errors = exc_info.value.errors()
        assert any(
            f"must be at least {DISPLAY_NAME_MIN_LENGTH} characters long" in str(error)
            for error in errors
        )

    def test_display_name_maximum_length(self):
        """Test maximum length validation."""
        long_name = "A" * (DISPLAY_NAME_MAX_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            UserDisplayNameUpdateSchema(display_name=long_name)

        errors = exc_info.value.errors()
        assert any(
            f"must be no more than {DISPLAY_NAME_MAX_LENGTH} characters long"
            in str(error)
            for error in errors
        )

    def test_display_name_contains_spaces(self):
        """Test that display names with spaces are rejected."""
        names_with_spaces = [
            "John Doe",
            "Alice Smith",
            "João Silva",
            "María García",
            "A B C D E F G H I J",
            "user name",
            "test user",
            "user 123",
        ]

        for name in names_with_spaces:
            with pytest.raises(ValidationError) as exc_info:
                UserDisplayNameUpdateSchema(display_name=name)

            errors = exc_info.value.errors()
            assert any("cannot contain spaces" in str(error) for error in errors)

    def test_display_name_invalid_characters(self):
        """Test that invalid characters are rejected."""
        invalid_names = [
            "user@domain.com",  # @ symbol
            "user#123",  # # symbol
            "user$name",  # $ symbol
            "user%name",  # % symbol
            "user&name",  # & symbol
            "user*name",  # * symbol
            "user+name",  # + symbol
            "user=name",  # = symbol
            "user[name]",  # brackets
            "user{name}",  # braces
            "user|name",  # pipe
            "user\\name",  # backslash
            "user/name",  # forward slash
            "user?name",  # question mark
            "user!name",  # exclamation
            "user,name",  # comma
            "user;name",  # semicolon
            "user:name",  # colon
            'user"name',  # quotes
            "user'name",  # apostrophe
            "user`name",  # backtick
            "user~name",  # tilde
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                UserDisplayNameUpdateSchema(display_name=name)

            errors = exc_info.value.errors()
            assert any(
                "can only contain letters, numbers, hyphens, underscores, and dots"
                in str(error)
                for error in errors
            )

    def test_display_name_whitespace_trimming(self):
        """Test that whitespace is properly trimmed."""
        schema = UserDisplayNameUpdateSchema(display_name="  JohnDoe  ")
        assert schema.display_name == "JohnDoe"

    def test_edge_cases(self):
        """Test edge cases for display name validation."""
        # Exactly 2 characters (minimum)
        schema = UserDisplayNameUpdateSchema(display_name="Jo")
        assert schema.display_name == "Jo"

        # Exactly 150 characters (maximum)
        max_char_name = "A" * DISPLAY_NAME_MAX_LENGTH
        schema = UserDisplayNameUpdateSchema(display_name=max_char_name)
        assert schema.display_name == max_char_name

        # Mixed valid characters
        schema = UserDisplayNameUpdateSchema(display_name="João_Silva-123")
        assert schema.display_name == "João_Silva-123"

        # All valid characters including dots
        schema = UserDisplayNameUpdateSchema(display_name="abc123_-Àÿ.")
        assert schema.display_name == "abc123_-Àÿ."


@pytest.mark.unit
class TestUserDisplayNameResponseSchema:
    """Test suite for UserDisplayNameResponseSchema."""

    def test_valid_response_schema(self):
        """Test that valid response data creates schema correctly."""
        response_data = {
            "id": 1,
            "display_name": "JohnDoe",
            "message": "Display name updated successfully",
        }

        schema = UserDisplayNameResponseSchema(**response_data)
        assert schema.id == 1
        assert schema.display_name == "JohnDoe"
        assert schema.message == "Display name updated successfully"

    def test_default_message(self):
        """Test that default message is set correctly."""
        response_data = {"id": 1, "display_name": "JohnDoe"}

        schema = UserDisplayNameResponseSchema(**response_data)
        assert schema.message == "Display name updated successfully"

    def test_custom_message(self):
        """Test that custom message can be set."""
        response_data = {
            "id": 1,
            "display_name": "JohnDoe",
            "message": "Custom success message",
        }

        schema = UserDisplayNameResponseSchema(**response_data)
        assert schema.message == "Custom success message"
