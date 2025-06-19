from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.core.repositories.wikiclip import WikiClipRepository
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient


@pytest.mark.integration
class TestWikiClipEndpoints:
    """Integration tests for WikiClip API endpoints."""

    @pytest.fixture
    async def authenticated_client(
        self,
        test_client: EHPTestClient,
        setup_jwt,
        test_db_manager: DBManager,
    ):
        auth_repository = AuthenticationRepository(
            test_db_manager.get_session(), Authentication
        )
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        await auth_repository.create(self.authentication)
        await user_repository.create(self.user)
        self.authentication.user = self.user
        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            self.authentication.id,
            self.authentication.user_email,
            with_refresh=False,
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    def setup_method(self):
        """Setup test data for each test method."""
        self.authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd="hashedpassword",  # Simulating a pre-hashed password
            is_active="1",
            is_confirmed="1",
            retry_count=0,
        )
        self.user = User(
            id=123,
            full_name="Mock User",
            created_at=datetime.now(),
            auth_id=self.authentication.id,
        )
        self.test_datetime = datetime(2024, 6, 16, 12, 0, 0)
        self.valid_wikiclip_data = {
            "title": "Test WikiClip Article",
            "content": "This is a test content for the WikiClip article.",
            "url": "https://example.com/test-article",
            "created_at": self.test_datetime.isoformat(),
            "related_links": [
                "https://example.com/related1",
                "https://example.com/related2",
            ],
        }
        self.created_wikiclip = WikiClip(
            id=1,
            title="Test WikiClip Article",
            content="This is a test content for the WikiClip article.",
            url="https://example.com/test-article",
            created_at=self.test_datetime,
            related_links=[
                "https://example.com/related1",
                "https://example.com/related2",
            ],
            user_id=self.user.id,
        )

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_success(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test successful WikiClip creation."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.exists.return_value = False
        mock_repo.create.return_value = self.created_wikiclip

        # Make request
        response = authenticated_client.post(
            "/wikiclip/", json=self.valid_wikiclip_data, include_auth=True
        )

        # Assertions
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == 1
        assert response_data["title"] == "Test WikiClip Article"
        assert response_data["url"] == "https://example.com/test-article"
        assert response_data["created_at"] == self.test_datetime.isoformat()

        # Verify repository calls
        mock_repo.exists.assert_called_once_with(
            "https://example.com/test-article",
            date.today(),
            "Test WikiClip Article",
            self.user.id,
        )
        mock_repo.create.assert_called_once()

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_duplicate_url(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation with duplicate URL."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.exists.return_value = True

        # Make request
        response = authenticated_client.post(
            "/wikiclip/", json=self.valid_wikiclip_data, include_auth=True
        )

        # Assertions
        assert response.status_code == 409
        assert "A WikiClip with this URL already exists" in response.json()["detail"]

        # Verify repository calls
        mock_repo.exists.assert_called_once_with(
            "https://example.com/test-article",
            date.today(),
            "Test WikiClip Article",
            self.user.id,
        )
        mock_repo.create.assert_not_called()

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_repository_error(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation with repository error."""
        # Setup mock repository
        exc = Exception("Database error")
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.exists.return_value = False
        mock_repo.create.side_effect = exc

        # Make request
        with patch(
            "ehp.utils.base.log_error"
        ):
            # This will capture the log error call
            response = authenticated_client.post(
                "/wikiclip/", json=self.valid_wikiclip_data, include_auth=True
            )

        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

        # Verify repository calls
        mock_repo.exists.assert_called_once()
        mock_repo.create.assert_called_once()

    def test_save_wikiclip_invalid_data(self, authenticated_client: EHPTestClient):
        """Test WikiClip creation with invalid data."""
        invalid_data = {
            "title": "",  # Empty title should fail validation
            "content": "Valid content",
            "url": "https://example.com/test",
            "created_at": self.test_datetime.isoformat(),
        }

        response = authenticated_client.post(
            "/wikiclip/", json=invalid_data, include_auth=True
        )

        assert response.status_code == 422  # Validation error

    def test_save_wikiclip_missing_fields(self, authenticated_client: EHPTestClient):
        """Test WikiClip creation with missing required fields."""
        incomplete_data = {
            "title": "Test Title",
            # Missing content, url, created_at
        }

        response = authenticated_client.post(
            "/wikiclip/", json=incomplete_data, include_auth=True
        )

        assert response.status_code == 422  # Validation error

    def test_save_wikiclip_long_title(self, authenticated_client: EHPTestClient):
        """Test WikiClip creation with title exceeding length limit."""
        invalid_data = self.valid_wikiclip_data.copy()
        invalid_data["title"] = "x" * 501  # Exceeds 500 character limit

        response = authenticated_client.post(
            "/wikiclip/", json=invalid_data, include_auth=True
        )

        assert response.status_code == 422  # Validation error

    def test_save_wikiclip_long_url(self, authenticated_client: EHPTestClient):
        """Test WikiClip creation with URL exceeding length limit."""
        invalid_data = self.valid_wikiclip_data.copy()
        invalid_data["url"] = (
            "https://example.com/" + "x" * 2000
        )  # Exceeds 2000 character limit

        response = authenticated_client.post(
            "/wikiclip/", json=invalid_data, include_auth=True
        )

        assert response.status_code == 422  # Validation error

    def test_save_wikiclip_too_many_related_links(
        self, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation with too many related links."""
        invalid_data = self.valid_wikiclip_data.copy()
        invalid_data["related_links"] = [
            f"https://example{i}.com" for i in range(101)
        ]  # Exceeds 100 link limit

        response = authenticated_client.post(
            "/wikiclip/", json=invalid_data, include_auth=True
        )

        assert response.status_code == 422  # Validation error

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_success(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test successful WikiClip retrieval."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.created_wikiclip

        # Make request
        response = authenticated_client.get("/wikiclip/1", include_auth=True)

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == 1
        assert response_data["title"] == "Test WikiClip Article"
        assert response_data["url"] == "https://example.com/test-article"
        assert response_data["created_at"] == self.test_datetime.isoformat()

        # Verify repository calls
        mock_repo.get_by_id.assert_called_once_with(1)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_not_found(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip retrieval when not found."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = None

        # Make request
        response = authenticated_client.get("/wikiclip/999", include_auth=True)

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "WikiClip not found"

        # Verify repository calls
        mock_repo.get_by_id.assert_called_once_with(999)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_repository_error(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip retrieval with repository error."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id.side_effect = Exception("Database error")

        # Make request
        response = authenticated_client.get("/wikiclip/1", include_auth=True)

        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

        # Verify repository calls
        mock_repo.get_by_id.assert_called_once_with(1)

    def test_get_wikiclip_invalid_id(self, authenticated_client: EHPTestClient):
        """Test WikiClip retrieval with invalid ID format."""
        response = authenticated_client.get("/wikiclip/invalid", include_auth=True)

        # Should return 422 for invalid path parameter type
        assert response.status_code == 422

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_without_related_links(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation without related links (optional field)."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.exists.return_value = False

        created_wikiclip_no_links = WikiClip(
            id=2,
            title="Test WikiClip No Links",
            content="Test content without related links",
            url="https://example.com/no-links",
            created_at=self.test_datetime,
            related_links=None,
        )
        mock_repo.create.return_value = created_wikiclip_no_links

        # Test data without related_links
        test_data = {
            "title": "Test WikiClip No Links",
            "content": "Test content without related links",
            "url": "https://example.com/no-links",
            "created_at": self.test_datetime.isoformat(),
        }

        # Make request
        response = authenticated_client.post(
            "/wikiclip/", json=test_data, include_auth=True
        )

        # Assertions
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == 2
        assert response_data["title"] == "Test WikiClip No Links"
        assert response_data["url"] == "https://example.com/no-links"

        # Verify repository calls
        mock_repo.exists.assert_called_once()
        mock_repo.create.assert_called_once()
