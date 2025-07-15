from typing import ClassVar
import pytest

from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.profile import Profile
from ehp.core.models.db.user import User
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils import constants
from ehp.utils.authentication import hash_password


@pytest.mark.integration
class TestReadingSettingsEndpoints:
    """Integration tests for reading settings endpoints."""

    ORIGINAL_PASSWORD: ClassVar[str] = "Te$tPassword123"

    @pytest.fixture(scope="function")
    async def authenticated_client(
        self, test_client: EHPTestClient, setup_jwt, test_db_manager: DBManager
    ):
        """Setup authenticated client with user data, following the project's working pattern."""
        profile_repository = BaseRepository(test_db_manager.get_session(), Profile)
        for profilename, profilecode in constants.PROFILE_IDS.items():
            await profile_repository.create(
                Profile(id=profilecode, name=profilename, code=profilename.lower())
            )

        authentication = Authentication(
            id=123,
            user_name="mockuser",
            user_email="mock@example.com",
            user_pwd=hash_password(self.ORIGINAL_PASSWORD),
            is_active="1",
            is_confirmed="1",
            retry_count=0,
            profile_id=constants.PROFILE_IDS["user"],
        )
        user = User(
            id=123,
            full_name="Mock User",
            auth_id=authentication.id,
            reading_settings=None,
        )

        auth_repository = AuthenticationRepository(test_db_manager.get_session())
        user_repository = BaseRepository(test_db_manager.get_session(), User)
        await auth_repository.create(authentication)
        await user_repository.create(user)

        authentication.user = user

        session_manager = SessionManager()
        authenticated_token = session_manager.create_session(
            str(authentication.id), authentication.user_email, with_refresh=False
        )
        test_client.auth_token = authenticated_token.access_token
        yield test_client

    async def test_get_reading_settings_defaults(
        self, authenticated_client: EHPTestClient
    ):
        response = authenticated_client.get(
            "/users/reading-settings", include_auth=True
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["font_size"] == "Medium"
        assert data["fonts"]["headline"] == "System"

    async def test_create_and_get_reading_settings(
        self, authenticated_client: EHPTestClient
    ):
        settings = {
            "font_size": "Large",
            "font_weight": "Bold",
            "line_spacing": "Wide",
            "color_mode": "Dark",
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
        }
        create_response = authenticated_client.post(
            "/users/reading-settings", json=settings, include_auth=True
        )
        assert create_response.status_code == 201, create_response.text

        get_response = authenticated_client.get(
            "/users/reading-settings", include_auth=True
        )
        assert get_response.status_code == 200, get_response.text
        assert get_response.json() == settings

    async def test_update_reading_settings_partial_fonts_merge(
        self, authenticated_client: EHPTestClient
    ):
        initial_settings = {
            "font_size": "Medium",
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
        }
        create_response = authenticated_client.post(
            "/users/reading-settings", json=initial_settings, include_auth=True
        )
        assert create_response.status_code == 201, create_response.text

        partial_fonts_update = {"fonts": {"headline": "Arial"}}
        response = authenticated_client.put(
            "/users/reading-settings", json=partial_fonts_update, include_auth=True
        )
        assert response.status_code == 200, response.text

        data = response.json()
        assert data["fonts"]["headline"] == "Arial"
        assert data["fonts"]["body"] == "System"
        assert data["font_size"] == "Medium"

    async def test_reading_settings_unauthenticated(self, test_client: EHPTestClient):
        assert test_client.get("/users/reading-settings").status_code == 403
        assert test_client.post("/users/reading-settings", json={}).status_code == 403
        assert test_client.put("/users/reading-settings", json={}).status_code == 403

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "font_size": 123,
                "fonts": {"headline": "a", "body": "b", "caption": "c"},
                "font_weight": "n",
                "line_spacing": "s",
                "color_mode": "d",
            },
            {
                "font_size": "a",
                "fonts": "invalid",
                "font_weight": "n",
                "line_spacing": "s",
                "color_mode": "d",
            },
        ],
    )
    def test_create_with_invalid_data(
        self, authenticated_client: EHPTestClient, payload: dict
    ):
        response = authenticated_client.post(
            "/users/reading-settings", json=payload, include_auth=True
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("payload", [{"font_size": 123}, {"fonts": "invalid"}])
    def test_update_with_invalid_data(
        self, authenticated_client: EHPTestClient, payload: dict
    ):
        response = authenticated_client.put(
            "/users/reading-settings", json=payload, include_auth=True
        )
        assert response.status_code == 422
