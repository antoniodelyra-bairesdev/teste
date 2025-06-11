from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ehp.config import settings
from ehp.tests.utils.mocks import (
    patch_elasticsearch,
    patch_email,
    patch_redis,
    setup_mock_authentication,
)


class EHPTestClient:
    """
    Test client for EHP API that provides helper methods for making
    API requests with appropriate headers and mocked dependencies.
    """

    def __init__(self, app: FastAPI):
        self.app = app
        self.client = TestClient(app)
        self.api_key = settings.API_KEY_VALUE
        self.auth_token = "test-auth-token"

        # Setup patchers
        self.redis_patch, self.get_redis_patch, self.mock_redis = patch_redis()
        self.es_patch, self.mock_es = patch_elasticsearch()
        self.smtp_patch, self.send_notification_patch = patch_email()

        # Start patches
        self.redis_patch.start()
        self.get_redis_patch.start()
        self.es_patch.start()
        self.smtp_patch.start()
        self.send_notification_patch.start()

    def start(self):
        self.client.__enter__()

    def stop(self):
        """Stop the TestClient."""
        self.client.__exit__(None, None, None)

    def __del__(self):
        """Clean up by stopping all patches."""
        self._stop_patches()

    def _stop_patches(self):
        """Stop all active patches."""
        for patcher in [
            self.redis_patch,
            self.get_redis_patch,
            self.es_patch,
            self.smtp_patch,
            self.send_notification_patch,
        ]:
            try:
                patcher.stop()
            except RuntimeError:
                # Patch might already be stopped
                pass

    def get_headers(self, include_auth: bool = False) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"X-Api-Key": self.api_key}
        if include_auth:
            headers["X-Token-Auth"] = self.auth_token
        return headers

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        include_auth: bool = False,
        **kwargs
    ) -> Any:
        """Make a GET request to the API."""
        headers = self.get_headers(include_auth)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        return self.client.get(url, params=params, headers=headers, **kwargs)

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        include_auth: bool = False,
        **kwargs
    ) -> Any:
        """Make a POST request to the API."""
        headers = self.get_headers(include_auth)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        return self.client.post(url, json=json, headers=headers, **kwargs)

    def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        include_auth: bool = False,
        **kwargs
    ) -> Any:
        """Make a PUT request to the API."""
        headers = self.get_headers(include_auth)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        return self.client.put(url, json=json, headers=headers, **kwargs)

    def delete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        include_auth: bool = False,
        **kwargs
    ) -> Any:
        """Make a DELETE request to the API."""
        headers = self.get_headers(include_auth)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        return self.client.delete(url, params=params, headers=headers, **kwargs)

    def setup_authentication(self, user_data: Optional[Dict[str, Any]] = None):
        """
        Setup mock authentication with the provided user data.
        Returns the patches and mock auth object.
        """
        return setup_mock_authentication(None, user_data)


class AsyncEHPTestClient(EHPTestClient):
    """
    Test client for EHP API that supports async testing with
    appropriate mocking of async dependencies.
    """

    async def setup_async_session(self, db_session, mock_data=None):
        """Setup async session with mock data."""
        # Implementation would depend on specific test requirements
        pass
