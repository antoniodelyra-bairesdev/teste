from datetime import datetime
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
from ehp.utils.authentication import hash_password


@pytest.mark.integration
class TestWikiClipEndpointsWithReadingSettings:
    """Integration tests for WikiClip endpoints with reading settings injection."""

    def setup_method(self):
        self.authentication = Authentication(
            id=100,
            user_name="readingsettingsuser",
            user_email="readingsettings@example.com",
            user_pwd=hash_password("Te$tPassword123"),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
        )
        self.user = User(
            id=100,
            full_name="Reading Settings User",
            created_at=datetime.now(),
            auth_id=self.authentication.id,
        )

    @pytest.fixture
    async def authenticated_client(
        self,
        test_client: EHPTestClient,
        setup_jwt,
        test_db_manager: DBManager,
    ):
        """Create authenticated client with user and reading settings."""
        # Create authentication and user
        auth_repository = AuthenticationRepository(test_db_manager.get_session())
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        
        await auth_repository.create(self.authentication)
        await user_repository.create(self.user)
        self.authentication.user = self.user
        
        # Create session token
        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            self.authentication.id,
            self.authentication.user_email,
            with_refresh=False,
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    async def test_get_wikiclip_includes_reading_settings(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that GET /wikiclip/{id} includes reading settings in response."""
        # Set user reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        self.user.reading_settings = {
            "font_size": "Large",
            "color_mode": "Dark",
            "font_weight": "Bold",
            "line_spacing": "Wide",
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
        }
        await user_repo.update(self.user)

        # Create test wikiclip
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        test_wikiclip = WikiClip(
            id=1,
            title="Test Article with Settings",
            content="This article should include reading settings",
            url="https://example.com/test-settings",
            created_at=datetime.now(),
            user_id=self.user.id,
        )
        await wikiclip_repo.create(test_wikiclip)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/1", include_auth=True)
        assert response.status_code == 200
        
        response_data = response.json()
        assert "reading_settings" in response_data
        assert response_data["reading_settings"]["font_size"] == "Large"
        assert response_data["reading_settings"]["color_mode"] == "Dark"
        assert response_data["reading_settings"]["font_weight"] == "Bold"
        assert response_data["reading_settings"]["line_spacing"] == "Wide"
        assert response_data["reading_settings"]["fonts"]["body"] == "Georgia"

    async def test_get_my_pages_includes_reading_settings_in_metadata(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that GET /wikiclip/my includes reading settings in metadata."""
        # Set user reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        self.user.reading_settings = {
            "font_size": "Medium",
            "color_mode": "Light",
            "fonts": {"body": "Arial"},
        }
        await user_repo.update(self.user)

        # Create test wikiclips
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        for i in range(3):
            wikiclip = WikiClip(
                id=i + 1,
                title=f"My Article {i + 1}",
                content=f"Content for article {i + 1}",
                url=f"https://example.com/article-{i + 1}",
                created_at=datetime.now(),
                user_id=self.user.id,
            )
            await wikiclip_repo.create(wikiclip)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/my", include_auth=True)
        assert response.status_code == 200
        
        response_data = response.json()
        assert "metadata" in response_data
        assert "reading_settings" in response_data["metadata"]
        metadata_settings = response_data["metadata"]["reading_settings"]
        assert metadata_settings["font_size"] == "Medium"
        assert metadata_settings["color_mode"] == "Light"
        assert metadata_settings["fonts"]["body"] == "Arial"

    async def test_get_trending_includes_reading_settings_in_metadata(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that GET /wikiclip/trending includes reading settings in metadata."""
        # Set user reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        self.user.reading_settings = {
            "font_size": "Extra Large",
            "color_mode": "Sepia",
            "line_spacing": "Extra Wide",
        }
        await user_repo.update(self.user)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/trending", include_auth=True)
        assert response.status_code == 200
        
        response_data = response.json()
        assert "data" in response_data
        assert "metadata" in response_data
        metadata_settings = response_data["metadata"]["reading_settings"]
        assert metadata_settings["font_size"] == "Extra Large"
        assert metadata_settings["color_mode"] == "Sepia"
        assert metadata_settings["line_spacing"] == "Extra Wide"

    async def test_search_wikiclips_includes_reading_settings_in_metadata(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that GET /wikiclip/ (search) includes reading settings in metadata."""
        # Set user reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        self.user.reading_settings = {
            "font_size": "Small",
            "fonts": {"headline": "Times", "body": "Helvetica"},
        }
        await user_repo.update(self.user)

        # Test endpoint
        response = authenticated_client.get(
            "/wikiclip/",
            params={"search_term": "test", "page": 1, "size": 10},
            include_auth=True
        )
        assert response.status_code == 200
        
        response_data = response.json()
        assert "metadata" in response_data
        metadata_settings = response_data["metadata"]["reading_settings"]
        assert metadata_settings["font_size"] == "Small"
        assert metadata_settings["fonts"]["headline"] == "Times"
        assert metadata_settings["fonts"]["body"] == "Helvetica"

    async def test_suggested_wikiclips_includes_reading_settings_in_metadata(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that GET /wikiclip/suggested includes reading settings in metadata."""
        # Set user reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        self.user.reading_settings = {
            "font_size": "Medium",
            "fonts": {"headline": "Times", "body": "Helvetica", "caption": "Arial"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Light",
        }
        await user_repo.update(self.user)

        # Create test wikiclip
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        test_wikiclip = WikiClip(
            id=1,
            title="Suggested Article",
            content="This is a suggested article",
            url="https://example.com/suggested",
            created_at=datetime.now(),
            user_id=self.user.id,
        )
        await wikiclip_repo.create(test_wikiclip)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/suggested", include_auth=True)
        assert response.status_code == 200
        
        response_data = response.json()
        assert "metadata" in response_data
        metadata_settings = response_data["metadata"]["reading_settings"]
        assert metadata_settings["font_size"] == "Medium"
        assert metadata_settings["fonts"]["headline"] == "Times"
        assert metadata_settings["color_mode"] == "Light"

    async def test_user_without_reading_settings_uses_defaults(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that user without reading settings gets default values."""
        # Ensure user has no reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        self.user.reading_settings = None
        await user_repo.update(self.user)

        # Create test wikiclip
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        test_wikiclip = WikiClip(
            id=1,
            title="Default Settings Article",
            content="This article should use default settings",
            url="https://example.com/default-settings",
            created_at=datetime.now(),
            user_id=self.user.id,
        )
        await wikiclip_repo.create(test_wikiclip)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/1", include_auth=True)
        assert response.status_code == 200
        
        response_data = response.json()
        assert "reading_settings" in response_data
        default_settings = response_data["reading_settings"]
        assert default_settings["font_size"] == "Medium"
        assert default_settings["color_mode"] == "Default"
        assert default_settings["fonts"]["body"] == "System"

    async def test_partial_reading_settings_merged_with_defaults(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that partial reading settings are merged with defaults."""
        # Set partial reading settings
        user_repo = BaseRepository(test_db_manager.get_session(), User)
        partial_settings = {
            "font_size": "Large",
            "color_mode": "Dark",
        }
        self.user.reading_settings = partial_settings
        await user_repo.update(self.user)

        # Create test wikiclip
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        test_wikiclip = WikiClip(
            id=1,
            title="Partial Settings Article",
            content="This article should merge partial settings with defaults",
            url="https://example.com/partial-settings",
            created_at=datetime.now(),
            user_id=self.user.id,
        )
        await wikiclip_repo.create(test_wikiclip)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/1", include_auth=True)
        assert response.status_code == 200
        
        response_data = response.json()
        merged_settings = response_data["reading_settings"]
        assert merged_settings["font_size"] == "Large"
        assert merged_settings["color_mode"] == "Dark"
        assert "font_weight" in merged_settings
        assert "line_spacing" in merged_settings
        assert "fonts" in merged_settings

    async def test_unauthenticated_request_no_reading_settings(
        self, test_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that unauthenticated requests don't include reading settings."""
        # Create test wikiclip
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        test_wikiclip = WikiClip(
            id=1,
            title="Public Article",
            content="This is public content",
            url="https://example.com/public",
            created_at=datetime.now(),
            user_id=100,
        )
        await wikiclip_repo.create(test_wikiclip)

        # Test endpoint without authentication
        response = test_client.get("/wikiclip/1", include_auth=False)
        assert response.status_code in [401, 403]

    async def test_wikiclip_content_endpoint_works_without_reading_settings(
        self, authenticated_client: EHPTestClient, test_db_manager: DBManager
    ):
        """Test that content endpoint works without reading settings injection."""
        # Create test wikiclip
        wikiclip_repo = WikiClipRepository(test_db_manager.get_session())
        test_wikiclip = WikiClip(
            id=1,
            title="Test Content Article",
            content="This is the plain text content that should be returned.",
            url="https://example.com/test-content",
            created_at=datetime.now(),
            user_id=self.user.id,
        )
        await wikiclip_repo.create(test_wikiclip)

        # Test endpoint
        response = authenticated_client.get("/wikiclip/1/content", include_auth=True)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == "This is the plain text content that should be returned."
