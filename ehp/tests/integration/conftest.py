from dataclasses import dataclass
from typing import Dict, Any

import httpx
import pytest

from ehp.base.jwt_helper import TokenPayload
from ehp.base.session import SessionManager
from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.profile import Profile
from ehp.core.models.db.user import User
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.core.repositories.user import UserRepository
from ehp.db.db_manager import DBManager
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils import constants
from ehp.utils.authentication import hash_password
from ehp.utils.date_utils import timezone_now


@dataclass
class AuthenticatedClientProxy:
    """Proxy for authenticated client operations.
    This class provides methods to interact with the API using an authenticated client.
    It includes methods for making GET, POST, PUT, and DELETE requests with optional authentication headers."""

    user: User
    auth: Authentication
    session_data: TokenPayload
    test_client: EHPTestClient

    def get_headers(self, include_auth: bool = False) -> Dict[str, str]:
        return self.test_client.get_headers(include_auth)

    def get(
        self,
        url: str,
        params: Dict[str, Any] | None = None,
        include_auth: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        return self.test_client.get(url, params, include_auth, **kwargs)

    def post(
        self,
        url: str,
        json: Dict[str, Any] | None = None,
        include_auth: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        return self.test_client.post(url, json, include_auth, **kwargs)

    def put(
        self,
        url: str,
        json: Dict[str, Any] | None = None,
        include_auth: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        return self.test_client.put(url, json, include_auth, **kwargs)

    def delete(
        self,
        url: str,
        params: Dict[str, Any] | None = None,
        include_auth: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        return self.test_client.delete(url, params, include_auth, **kwargs)


USER_ID = 123
AUTH_ID = 123


@pytest.fixture
async def authenticated_client(
    test_client: EHPTestClient, setup_jwt: None, test_db_manager: DBManager
):
    """Fixture to create an authenticated client for testing.
    This fixture sets up a mock user and authentication, then returns an AuthenticatedClientProxy instance.
    It uses the provided test client and database manager to create the necessary authentication and user records.
    """
    del setup_jwt  # Used only to invoke the fixture
    session = test_db_manager.get_session()
    profile_repository = BaseRepository(test_db_manager.get_session(), Profile)
    for profilename, profilecode in constants.PROFILE_IDS.items():
        _ = await profile_repository.create(
            Profile(
                id=profilecode,
                name=profilename,
                code=profilename.lower(),
            )
        )

    auth_repo = AuthenticationRepository(session)
    user_repo = UserRepository(session)

    authentication = Authentication(
        id=AUTH_ID,
        user_name="mockuser",
        user_email="mock@example.com",
        user_pwd=hash_password("Te$tPassword123"),  # Using hash_password utility
        is_active="1",
        is_confirmed="1",
        retry_count=0,
    )
    user = User(
        id=USER_ID,
        full_name="Mock User",
        created_at=timezone_now(),
        auth_id=authentication.id,
    )

    _ = await auth_repo.create(authentication)
    _ = await user_repo.create(user)

    authentication.user = user

    _ = await auth_repo.update(authentication)

    session_manager = SessionManager()
    authentication_payload = session_manager.create_session(
        str(authentication.id), authentication.user_email, with_refresh=False
    )

    test_client.auth_token = authentication_payload.access_token
    return AuthenticatedClientProxy(
        user,
        authentication,
        authentication_payload,
        test_client,
    )
