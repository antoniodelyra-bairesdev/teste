from datetime import datetime
from unittest.mock import AsyncMock, patch
from ehp.base.session import SessionManager
import pytest

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password
from ehp.utils.constants import DISPLAY_NAME_MAX_LENGTH, DISPLAY_NAME_MIN_LENGTH
from pydantic import ValidationError


@pytest.mark.integration
class TestUserEndpoints:
    """Integration tests for User API endpoints."""

    @pytest.fixture
    async def authenticated_client(
        self,
        test_client: EHPTestClient,
        setup_jwt,
        test_db_manager: DBManager,
    ):
        """Setup authenticated client with user data."""
        authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd=hash_password("testpassword"),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
        )
        user = User(
            id=123,
            full_name="Mock User",
            display_name="mockuser",
            created_at=datetime.now(),
            auth_id=authentication.id,
        )

        auth_repository = AuthenticationRepository(
            test_db_manager.get_session()
        )
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        await auth_repository.create(authentication)
        await user_repository.create(user)
        authentication.user = user

        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            str(authentication.id),
            authentication.user_email,
            with_refresh=False,
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    @pytest.fixture
    async def another_user(self, test_db_manager: DBManager):
        """Create another user for testing access control."""
        authentication = Authentication(
            id=456,
            user_name="otheruser",
            user_email="other@example.com",
            user_pwd=hash_password("testpassword"),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
        )
        user = User(
            id=456,
            full_name="Other User",
            display_name="otheruser",
            created_at=datetime.now(),
            auth_id=authentication.id,
        )

        auth_repository = AuthenticationRepository(
            test_db_manager.get_session()
        )
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        await auth_repository.create(authentication)
        await user_repository.create(user)
        return user

    class TestUpdateDisplayName:
        """Test the PUT /users/display-name endpoint."""

        async def test_update_display_name_success(
            self, authenticated_client: EHPTestClient
        ):
            """Test successful display name update."""
            update_data = {"display_name": "UpdatedName"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo

                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = current_user

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["id"] == 123
            assert response_data["display_name"] == "UpdatedName"
            assert response_data["message"] == "Display name updated successfully"

        async def test_update_display_name_same_value(
            self, authenticated_client: EHPTestClient
        ):
            """Test updating to the same display name (should return unchanged message)."""
            update_data = {"display_name": "mockuser"}  # Same as current name

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                mock_repo.get_by_id.return_value = current_user

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["display_name"] == "mockuser"
            assert (
                response_data["message"]
                == "Display name unchanged (same value provided)"
            )

        async def test_update_display_name_user_not_found(
            self, authenticated_client: EHPTestClient
        ):
            """Test updating display name for non-existent user."""
            update_data = {"display_name": "NewName"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                mock_repo.get_by_id.return_value = None

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]

        async def test_update_display_name_already_exists(
            self, authenticated_client: EHPTestClient
        ):
            """Test updating to a display name that already exists."""
            update_data = {"display_name": "otheruser"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = True

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 409
            assert "This display name is already taken" in response.json()["detail"]

        async def test_update_display_name_validation_errors(
            self, authenticated_client: EHPTestClient
        ):
            """Test validation errors for invalid display names."""
            invalid_cases = [
                {"display_name": ""},  # Empty
                {"display_name": "A"},  # Too short
                {"display_name": "A" * (DISPLAY_NAME_MAX_LENGTH + 1)},  # Too long
                {"display_name": "user@domain.com"},  # Invalid characters
                {"display_name": "user name"},  # Contains spaces
                {"display_name": "user,name"},  # Invalid characters
                {"display_name": "user;name"},  # Invalid characters
            ]

            expected_messages = [
                "Display name is required",
                f"Display name must be at least {DISPLAY_NAME_MIN_LENGTH} "
                "characters long",
                f"Display name must be no more than {DISPLAY_NAME_MAX_LENGTH} "
                "characters long",
                "Display name can only contain letters, numbers, hyphens, "
                "underscores, and dots",
                "Display name cannot contain spaces",
                "Display name can only contain letters, numbers, hyphens, "
                "underscores, and dots",
                "Display name can only contain letters, numbers, hyphens, "
                "underscores, and dots",
            ]

            for i, invalid_data in enumerate(invalid_cases):
                response = authenticated_client.put(
                    "/users/display-name", json=invalid_data, include_auth=True
                )

                assert response.status_code == 422
                response_detail = response.json()["detail"]

                # Check if the expected message is in the response detail
                # The response might be a list of validation errors or a string
                if isinstance(response_detail, list):
                    # If it's a list, check if any error contains our expected message
                    error_messages = [error.get("msg", "") for error in response_detail]
                    assert any(expected_messages[i] in msg for msg in error_messages), (
                        f"Expected '{expected_messages[i]}' in error messages: "
                        f"{error_messages}"
                    )
                else:
                    # If it's a string, check if it contains our expected message
                    assert expected_messages[i] in response_detail, (
                        f"Expected '{expected_messages[i]}' in response detail: "
                        f"{response_detail}"
                    )

        async def test_update_display_name_unauthenticated(
            self, test_client: EHPTestClient
        ):
            """Test updating display name without authentication."""
            update_data = {"display_name": "NewName"}

            response = test_client.put(
                "/users/display-name", json=update_data, include_auth=False
            )

            assert response.status_code == 403

        async def test_update_display_name_internal_error(
            self, authenticated_client: EHPTestClient
        ):
            """Test handling of internal server errors."""
            update_data = {"display_name": "NewName"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.side_effect = Exception("Database error")

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

        async def test_update_display_name_whitespace_trimming(
            self, authenticated_client: EHPTestClient
        ):
            """Test that whitespace is properly trimmed in display names."""
            update_data = {"display_name": "  TrimmedName  "}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                updated_user = User(
                    id=123, full_name="Mock User", display_name="TrimmedName"
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = updated_user

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 200
            assert response.json()["display_name"] == "TrimmedName"

        async def test_update_display_name_unicode_characters(
            self, authenticated_client: EHPTestClient
        ):
            """Test updating display name with unicode characters."""
            update_data = {"display_name": "JoãoSilva"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                updated_user = User(
                    id=123, full_name="Mock User", display_name="JoãoSilva"
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = updated_user

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 200
            assert response.json()["display_name"] == "JoãoSilva"

        async def test_update_display_name_valid_characters(
            self, authenticated_client: EHPTestClient
        ):
            """Test updating display name with all valid characters."""
            update_data = {"display_name": "user123_-Àÿ."}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                updated_user = User(
                    id=123, full_name="Mock User", display_name="user123_-Àÿ."
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = updated_user

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 200
            assert response.json()["display_name"] == "user123_-Àÿ."

        async def test_update_display_name_edge_cases(
            self, authenticated_client: EHPTestClient
        ):
            """Test edge cases for display name validation."""
            # Minimum length
            min_length_data = {"display_name": "AB"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                updated_user = User(id=123, full_name="Mock User", display_name="AB")
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = updated_user

                response = authenticated_client.put(
                    "/users/display-name", json=min_length_data, include_auth=True
                )

            assert response.status_code == 200
            assert response.json()["display_name"] == "AB"

            # Maximum length
            max_length_data = {"display_name": "A" * DISPLAY_NAME_MAX_LENGTH}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                updated_user = User(
                    id=123,
                    full_name="Mock User",
                    display_name="A" * DISPLAY_NAME_MAX_LENGTH,
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = updated_user

                response = authenticated_client.put(
                    "/users/display-name", json=max_length_data, include_auth=True
                )

            assert response.status_code == 200
            assert response.json()["display_name"] == "A" * DISPLAY_NAME_MAX_LENGTH

        async def test_update_display_name_validation_error_handling(
            self, authenticated_client: EHPTestClient
        ):
            """Test handling of ValidationError exceptions from Pydantic."""
            # This test covers the block of handling ValidationError exceptions
            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                mock_repo.get_by_id.return_value = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.side_effect = ValidationError.from_exception_data(
                    "ValidationError",
                    [
                        {
                            "type": "value_error",
                            "loc": ["display_name"],
                            "msg": "Display name is required",
                            "input": "",
                            "ctx": {"error": {}},
                        }
                    ],
                )

                response = authenticated_client.put(
                    "/users/display-name",
                    json={"display_name": "test"},
                    include_auth=True,
                )

            assert response.status_code == 422

        async def test_update_display_name_validation_error_with_empty_errors(
            self, authenticated_client: EHPTestClient
        ):
            """Test handling of ValidationError with empty errors list."""
            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                mock_repo.get_by_id.return_value = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.side_effect = ValidationError.from_exception_data(
                    "ValidationError", []
                )

                response = authenticated_client.put(
                    "/users/display-name",
                    json={"display_name": "test"},
                    include_auth=True,
                )

            assert response.status_code == 422

        async def test_update_display_name_with_dots(
            self, authenticated_client: EHPTestClient
        ):
            """Test updating display name with dots."""
            update_data = {"display_name": "user.name"}

            with patch("ehp.core.services.user.UserRepository") as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                current_user = User(
                    id=123, full_name="Mock User", display_name="mockuser"
                )
                updated_user = User(
                    id=123, full_name="Mock User", display_name="user.name"
                )
                mock_repo.get_by_id.return_value = current_user
                mock_repo.display_name_exists.return_value = False
                mock_repo.update.return_value = updated_user

                response = authenticated_client.put(
                    "/users/display-name", json=update_data, include_auth=True
                )

            assert response.status_code == 200
            assert response.json()["display_name"] == "user.name"
