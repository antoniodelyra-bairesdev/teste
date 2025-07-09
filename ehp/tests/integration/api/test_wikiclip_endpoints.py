from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
import pytest

from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.paging import PagedResponse
from ehp.core.models.schema.wikiclip import (
    WikiClipResponseSchema,
    WikiClipSearchSchema,
    WikiClipSearchSortStrategy,
)
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.core.repositories.wikiclip import WikiClipRepository
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password


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
            test_db_manager.get_session()
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
            user_pwd=hash_password("Te$tPassword123"),  # Using hash_password utility
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

    # ============================================================================
    # CREATE WIKICLIP TESTS
    # ============================================================================

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_success(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test successful WikiClip creation."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
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
        mock_repo.create.assert_called_once()

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_repository_error(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation with repository error."""
        # Setup mock repository
        exc = Exception("Database error")
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.create.side_effect = exc

        # Make request
        with patch("ehp.utils.base.log_error"):
            # This will capture the log error call
            response = authenticated_client.post(
                "/wikiclip/", json=self.valid_wikiclip_data, include_auth=True
            )

        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

        # Verify repository calls
        mock_repo.create.assert_called_once()

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_content_success(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test successful WikiClip content retrieval."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.return_value = self.created_wikiclip

        # Make request
        response = authenticated_client.get("/wikiclip/1/content", include_auth=True)

        # Assertions
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == "This is a test content for the WikiClip article."

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(1)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_content_not_found(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip content retrieval when not found."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.side_effect = HTTPException(status_code=404, detail="WikiClip not found")

        # Make request
        response = authenticated_client.get("/wikiclip/999/content", include_auth=True)

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "WikiClip not found"

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(999)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    @patch("ehp.core.services.wikiclip.log_error")
    def test_get_wikiclip_content_repository_error(
        self, mock_log_error, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip content retrieval with repository error."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        exc = Exception("Database error")
        mock_repo.get_by_id_or_404.side_effect = exc

        # Make request
        response = authenticated_client.get("/wikiclip/1/content", include_auth=True)

        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(1)
        
        # Verify error logging
        mock_log_error.assert_called_once_with(f"Error getting WikiClip content 1: {exc}")

    def test_get_wikiclip_content_invalid_id(self, authenticated_client: EHPTestClient):
        """Test WikiClip content retrieval with invalid ID format."""
        response = authenticated_client.get("/wikiclip/invalid/content", include_auth=True)

        # Should return 422 for invalid path parameter type
        assert response.status_code == 422

    def test_get_wikiclip_content_unauthenticated(self, test_client: EHPTestClient):
        """Test WikiClip content retrieval without authentication."""
        response = test_client.get("/wikiclip/1/content")

        # Should return 403 for unauthenticated request
        assert response.status_code == 403

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
    def test_save_wikiclip_without_related_links(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation without related links (optional field)."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo

        created_wikiclip_no_links = WikiClip(
            id=2,
            title="Test WikiClip No Links",
            content="Test content without related links",
            url="https://example.com/no-links",
            created_at=self.test_datetime,
            related_links=None,
            user_id=self.user.id,
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
        mock_repo.create.assert_called_once()

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_http_exception(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation that raises HTTPException."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        # Simulate an HTTPException being raised
        mock_repo.create.side_effect = HTTPException(status_code=409, detail="Conflict")

        # Make request
        response = authenticated_client.post(
            "/wikiclip/", json=self.valid_wikiclip_data, include_auth=True
        )

        # Assertions
        assert response.status_code == 409
        assert response.json()["detail"] == "Conflict"

        # Verify repository calls
        mock_repo.create.assert_called_once()

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_save_wikiclip_generic_exception(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip creation that raises a generic exception."""
        # Setup mock repository
        exc = Exception("Unexpected error")
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.create.side_effect = exc

        # Make request
        with patch("ehp.utils.base.log_error"):
            response = authenticated_client.post(
                "/wikiclip/", json=self.valid_wikiclip_data, include_auth=True
            )

        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

        # Verify repository calls
        mock_repo.create.assert_called_once()

    # ============================================================================
    # GET WIKICLIP TESTS
    # ============================================================================

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_success(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test successful WikiClip retrieval."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.return_value = self.created_wikiclip

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
        mock_repo.get_by_id_or_404.assert_called_once_with(1)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_not_found(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip retrieval when not found."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.side_effect = HTTPException(status_code=404, detail="WikiClip not found")

        # Make request
        response = authenticated_client.get("/wikiclip/999", include_auth=True)

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "WikiClip not found"

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(999)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_repository_error(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip retrieval with repository error."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.side_effect = Exception("Database error")

        # Make request
        response = authenticated_client.get("/wikiclip/1", include_auth=True)

        # Assertions
        assert response.status_code == 500
        assert (
            response.json()["detail"] == "Could not retrieve WikiClip due to an error"
        )

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(1)

    def test_get_wikiclip_invalid_id(self, authenticated_client: EHPTestClient):
        """Test WikiClip retrieval with invalid ID format."""
        response = authenticated_client.get("/wikiclip/invalid", include_auth=True)

        # Should return 422 for invalid path parameter type
        assert response.status_code == 422

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_http_exception(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip retrieval that raises HTTPException."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.side_effect = HTTPException(
            status_code=404, detail="Not Found"
        )

        # Make request
        response = authenticated_client.get("/wikiclip/1", include_auth=True)

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Not Found"

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(1)

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_get_wikiclip_generic_exception(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test WikiClip retrieval that raises a generic exception."""
        # Setup mock repository
        exc = Exception("Database error")
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id_or_404.side_effect = exc

        # Make request
        response = authenticated_client.get("/wikiclip/1", include_auth=True)

        # Assertions
        assert response.status_code == 500
        assert (
            response.json()["detail"] == "Could not retrieve WikiClip due to an error"
        )

        # Verify repository calls
        mock_repo.get_by_id_or_404.assert_called_once_with(1)

    # ============================================================================
    # DUPLICATE CHECK TESTS
    # ============================================================================

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_no_duplicate_found(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check when no duplicate is found."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.check_duplicate.return_value = (False, None, None)

        # Make request
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/new-article",
                "title": "New Article",
                "hours_threshold": 23,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["is_duplicate"] is False
        assert response_data["duplicate_article_id"] is None
        assert response_data["duplicate_created_at"] is None
        assert response_data["hours_difference"] is None
        assert response_data["threshold_hours"] == 23
        assert (
            "No duplicate found within 23 hours threshold" in response_data["message"]
        )

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_duplicate_found(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check when a duplicate is found."""
        # Setup mock repository
        duplicate_created_at = datetime(2024, 6, 16, 10, 0, 0)

        # Create mock duplicate article object
        mock_duplicate_article = WikiClip(
            id=123,
            title="Duplicate Article",
            content="Duplicate content",
            url="https://example.com/test-article",
            created_at=duplicate_created_at,
            user_id=self.user.id,
        )

        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        # Service expects (is_duplicate, duplicate_article_object, hours_difference)
        mock_repo.check_duplicate.return_value = (True, mock_duplicate_article, 2.5)

        # Make request
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 23,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["is_duplicate"] is True
        assert response_data["duplicate_article_id"] == 123
        assert response_data["duplicate_created_at"] == duplicate_created_at.isoformat()
        assert response_data["hours_difference"] == 2.5
        assert response_data["threshold_hours"] == 23
        assert "Duplicate article found" in response_data["message"]

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_invalid_threshold_too_low(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with invalid threshold (below minimum)."""
        # Make request with invalid threshold
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 0,  # Below minimum
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 422  # Validation error

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_invalid_threshold_too_high(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with invalid threshold (above maximum)."""
        # Make request with invalid threshold
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 97,  # Above maximum (96)
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_duplicate_check_missing_url(self, authenticated_client: EHPTestClient):
        """Test duplicate check with missing URL parameter."""
        # Make request without URL
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "title": "Test Article",
                "hours_threshold": 24,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_duplicate_check_missing_title(self, authenticated_client: EHPTestClient):
        """Test duplicate check with missing title parameter."""
        # Make request without title
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "hours_threshold": 24,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_duplicate_check_missing_threshold(
        self, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with missing hours_threshold parameter."""
        # Make request without hours_threshold
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_duplicate_check_unauthorized(self, test_client: EHPTestClient):
        """Test duplicate check without authentication."""
        # Make request without authentication
        response = test_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 24,
            },
            include_auth=False,
        )

        # Should return 400 or 403 because user is not authenticated for this protected endpoint
        assert response.status_code in [400, 403]

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_with_minimum_threshold(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with minimum hours threshold (1 hour)."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.check_duplicate.return_value = (False, None, None)

        # Make request with minimum threshold
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 1,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["threshold_hours"] == 1
        assert response_data["is_duplicate"] is False

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_with_maximum_threshold(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with maximum hours threshold (96 hours)."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.check_duplicate.return_value = (False, None, None)

        # Make request with maximum threshold
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 96,  # Maximum allowed
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["threshold_hours"] == 96
        assert response_data["is_duplicate"] is False

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_with_special_characters_in_params(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with special characters in URL and title."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.check_duplicate.return_value = (False, None, None)

        # URL and title with special characters
        test_url = "https://example.com/test-article?param=value&other=123"
        test_title = "Test Article: Special Characters & Symbols!"

        # Make request
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": test_url,
                "title": test_title,
                "hours_threshold": 12,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["threshold_hours"] == 12
        assert response_data["is_duplicate"] is False

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_repository_error(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test duplicate check with repository error."""
        # Setup mock repository to raise an exception
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.check_duplicate.side_effect = Exception("Database error")

        # Make request
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 12,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 500
        # Service returns detailed error message with the exception
        assert response.json()["detail"] == "Internal server error"

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_duplicate_check_response_schema_validation(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test that the response matches the expected schema structure."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo
        mock_repo.check_duplicate.return_value = (False, None, None)

        # Make request
        response = authenticated_client.get(
            "/wikiclip/duplicate-check",
            params={
                "url": "https://example.com/test-article",
                "title": "Test Article",
                "hours_threshold": 18,
            },
            include_auth=True,
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()

        # Verify all required fields are present
        required_fields = [
            "is_duplicate",
            "duplicate_article_id",
            "duplicate_created_at",
            "hours_difference",
            "threshold_hours",
            "message",
        ]
        for field in required_fields:
            assert field in response_data

        # Verify field types and values
        assert isinstance(response_data["is_duplicate"], bool)
        assert (
            isinstance(response_data["duplicate_article_id"], int)
            or response_data["duplicate_article_id"] is None
        )
        assert isinstance(response_data["threshold_hours"], int)
        assert isinstance(response_data["message"], str)

    # ============================================================================
    # SEARCH WIKICLIP TESTS
    # ============================================================================

    @patch("ehp.core.services.wikiclip.WikiClipRepository")
    def test_search_wikiclips_returns_entries_without_filters(
        self, mock_repo_class, authenticated_client: EHPTestClient
    ):
        """Test searching WikiClips without any filters."""
        # Setup mock repository
        mock_repo = AsyncMock(spec=WikiClipRepository)
        mock_repo_class.return_value = mock_repo

        # Mock search results
        mock_search_results = [
            self.created_wikiclip,
            WikiClip(
                id=2,
                title="Another Test Article",
                content="Content for another article.",
                url="https://example.com/another-article",
                created_at=self.test_datetime,
                related_links=[],
                user_id=self.user.id,
            ),
        ]
        mock_repo.search.return_value = mock_search_results
        mock_repo.count.return_value = len(mock_search_results)
        # Search parameters
        search = {
            "page": 1,
            "size": 10,
            "filter_by_user": False,  # No user filter
        }
        # Make request
        response = authenticated_client.get(
            "/wikiclip", params=search, include_auth=True
        )

        # Assertions
        assert response.status_code == 200
        response_data = PagedResponse[
            WikiClipResponseSchema, WikiClipSearchSchema
        ].model_validate_json(response.content)
        assert len(response_data.data) == len(mock_search_results)
        assert response_data.total_count == len(mock_search_results)
        assert response_data.page == search["page"]
        assert response_data.page_size == search["size"]
        assert response_data.filters is not None
        assert response_data.filters.search_term is None
        assert (
            response_data.filters.sort_by
            is WikiClipSearchSortStrategy.CREATION_DATE_DESC
        )
        assert response_data.filters.created_before is None
        assert response_data.filters.created_after is None
        assert response_data.filters.filter_by_user is False

    def test_search_wikiclips_invalid_sort_strategy(
        self, authenticated_client: EHPTestClient
    ):
        """Test searching WikiClips with an invalid sort strategy."""
        # Search parameters with invalid sort strategy
        search = {
            "page": 1,
            "size": 10,
            "sort_by": "invalid_sort_strategy",  # Invalid sort strategy
        }

        # Make request
        response = authenticated_client.get(
            "/wikiclip", params=search, include_auth=True
        )

        # Should return 422 for invalid query parameter
        assert response.status_code == 422

    async def test_search_wikiclips_with_filters(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test searching WikiClips with various filters."""
        # Setup mock repository
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        # Create test data
        userless_clip = WikiClip(
            id=5,
            title="Userless Article",
            content="Content for userless article.",
            url="https://example.com/userless-article",
            created_at=datetime(2024, 6, 15, 12, 0, 0),
            related_links=[],
            user_id=None,  # No user associated
        )
        clips = [
            WikiClip(
                id=1,
                title="Test Article 1",
                content="Content for test article 1.",
                url="https://example.com/test-article-1",
                created_at=datetime(2024, 6, 16, 12, 0, 0),
                related_links=[],
                user_id=self.user.id,
            ),
            WikiClip(
                id=2,
                title="Test Article 2",
                content="Content for test article 2.",
                url="https://example.com/test-article-2",
                created_at=datetime(2024, 6, 17, 12, 0, 0),
                related_links=[],
                user_id=self.user.id,
            ),
            WikiClip(
                id=3,
                title="Test Article 3",
                content="Content for test article 3.",
                url="https://example.com/test-article-3",
                created_at=datetime(2024, 6, 18, 12, 0, 0),
                related_links=[],
                user_id=self.user.id,
            ),
            userless_clip,
        ]
        # Save test data
        for clip in clips:
            await wikiclip_repo.create(clip)

        # Search parameters
        search = {
            "page": 1,
            "size": 2,
            "search_term": "Test Article",
            "sort_by": WikiClipSearchSortStrategy.CREATION_DATE_DESC,
            "created_before": datetime(2024, 6, 18, 12, 0, 0).isoformat(),
            "created_after": datetime(2024, 6, 16, 12, 0, 0).isoformat(),
            "filter_by_user": True,  # Filter by authenticated user
        }

        # Make request
        response = authenticated_client.get(
            "/wikiclip", params=search, include_auth=True
        )
        # Assertions
        assert response.status_code == 200
        response_data = PagedResponse[
            WikiClipResponseSchema, WikiClipSearchSchema
        ].model_validate_json(response.content)
        assert len(response_data.data) == 2
        assert response_data.total_count == 3
        assert response_data.page == search["page"]
        assert response_data.page_size == search["size"]
        assert response_data.filters is not None
        assert response_data.filters.search_term == "Test Article"
        assert (
            response_data.filters.sort_by
            is WikiClipSearchSortStrategy.CREATION_DATE_DESC
        )
        assert response_data.filters.created_before == datetime(2024, 6, 18, 12, 0, 0)
        assert response_data.filters.created_after == datetime(2024, 6, 16, 12, 0, 0)
        assert response_data.filters.filter_by_user is True
        # Verify that only clips created by the authenticated user are returned
        for clip in response_data.data:
            assert clip.id != userless_clip.id
            assert clip.created_at <= datetime(2024, 6, 18, 12, 0, 0)
            assert clip.created_at >= datetime(2024, 6, 16, 12, 0, 0)

    async def test_search_wikiclips_no_results(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test searching WikiClips with no results."""
        # Setup mock repository
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        # Create test data
        await wikiclip_repo.create(
            WikiClip(
                id=1,
                title="Existing Article",
                content="Content for existing article.",
                url="https://example.com/existing-article",
                created_at=datetime(2024, 6, 16, 12, 0, 0),
                related_links=[],
                user_id=self.user.id,
            )
        )

        # Search parameters that will yield no results
        search = {
            "page": 1,
            "size": 10,
            "search_term": "Nonexistent Article",
            "sort_by": WikiClipSearchSortStrategy.CREATION_DATE_DESC,
            "created_before": datetime(2024, 6, 15, 12, 0, 0).isoformat(),
            "created_after": datetime(2024, 6, 17, 12, 0, 0).isoformat(),
            "filter_by_user": True,
        }

        # Make request
        response = authenticated_client.get(
            "/wikiclip", params=search, include_auth=True
        )

        # Assertions
        assert response.status_code == 200
        response_data = PagedResponse[
            WikiClipResponseSchema, WikiClipSearchSchema
        ].model_validate_json(response.content)
        assert len(response_data.data) == 0
        assert response_data.total_count == 0
        assert response_data.page == search["page"]
        assert response_data.page_size == search["size"]
        assert response_data.filters is not None
        assert response_data.filters.search_term == "Nonexistent Article"
        assert (
            response_data.filters.sort_by
            is WikiClipSearchSortStrategy.CREATION_DATE_DESC
        )
        assert response_data.filters.created_before == datetime(2024, 6, 15, 12, 0, 0)
        assert response_data.filters.created_after == datetime(2024, 6, 17, 12, 0, 0)
        assert response_data.filters.filter_by_user is True

    async def test_search_wikiclips_second_page(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test searching WikiClips with pagination on the second page."""
        # Setup mock repository
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        # Create test data
        clips = [
            WikiClip(
                id=i,
                title=f"Test Article {i}",
                content=f"Content for test article {i}.",
                url=f"https://example.com/test-article-{i}",
                created_at=datetime(2024, 6, 16, 12, 0, 0),
                related_links=[],
                user_id=self.user.id,
            )
            for i in range(1, 21)  # Create 20 clips
        ]
        # Save test data
        for clip in clips:
            await wikiclip_repo.create(clip)

        # Search parameters for second page
        search = {
            "page": 2,
            "size": 10,
            "filter_by_user": True,  # Filter by authenticated user
        }

        # Make request
        response = authenticated_client.get(
            "/wikiclip", params=search, include_auth=True
        )

        # Assertions
        assert response.status_code == 200
        response_data = PagedResponse[
            WikiClipResponseSchema, WikiClipSearchSchema
        ].model_validate_json(response.content)
        assert len(response_data.data) == 10
        assert response_data.total_count == 20
        assert response_data.page == search["page"]
        assert response_data.page_size == search["size"]
        assert response_data.filters is not None
        assert response_data.filters.search_term is None
        assert (
            response_data.filters.sort_by
            is WikiClipSearchSortStrategy.CREATION_DATE_DESC
        )
        assert response_data.filters.created_before is None
        assert response_data.filters.created_after is None
        assert response_data.filters.filter_by_user is True
        # Verify that the clips returned are from the second page
        for clip in response_data.data:
            assert clip.id > 10
            assert clip.id <= 20

    async def test_search_wikiclips_created_at_asc(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test searching WikiClips with creation date ascending sort."""
        # Setup mock repository
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        # Create test data
        clips = [
            WikiClip(
                id=i,
                title=f"Test Article {i}",
                content=f"Content for test article {i}.",
                url=f"https://example.com/test-article-{i}",
                created_at=datetime(2024, 6, 16, 12, 0, 0) - timedelta(days=i),
                related_links=[],
                user_id=self.user.id,
            )
            for i in range(1, 6)  # Create 5 clips with different dates
        ]
        # Save test data
        for clip in clips:
            await wikiclip_repo.create(clip)

        # Search parameters with creation date ascending sort
        search = {
            "page": 1,
            "size": 5,
            "sort_by": WikiClipSearchSortStrategy.CREATION_DATE_ASC,
            "filter_by_user": True,  # Filter by authenticated user
        }

        # Make request
        response = authenticated_client.get(
            "/wikiclip", params=search, include_auth=True
        )

        # Assertions
        assert response.status_code == 200
        response_data = PagedResponse[
            WikiClipResponseSchema, WikiClipSearchSchema
        ].model_validate_json(response.content)
        assert len(response_data.data) == 5
        assert response_data.total_count == 5
        assert response_data.page == search["page"]
        assert response_data.page_size == search["size"]
        assert response_data.filters is not None
        assert response_data.filters.search_term is None
        assert (
            response_data.filters.sort_by
            is WikiClipSearchSortStrategy.CREATION_DATE_ASC
        )
        assert response_data.filters.created_before is None
        assert response_data.filters.created_after is None
        assert response_data.filters.filter_by_user is True

        # Verify that the clips are sorted by creation date ascending
        previous_date = None
        for clip in response_data.data:
            if previous_date:
                assert clip.created_at >= previous_date
            previous_date = clip.created_at
