import pytest
from fastapi.testclient import TestClient

from ehp.config import settings


@pytest.mark.unit
@pytest.mark.usefixtures("setup_jwt")
def test_root_endpoint(test_client: TestClient, api_key_header):
    """Test the root meta endpoint."""
    response = test_client.get("/_meta", headers=api_key_header)

    assert response.status_code == 200

    result = response.json()
    assert result["name"] == settings.APP_NAME
    assert result["version"] == settings.APP_VERSION
    assert "description" in result
    assert "time" in result


@pytest.mark.unit
@pytest.mark.skip(
    reason="Skipping test as current implementation does not require API key"
)
def test_root_endpoint_unauthorized(test_client: TestClient):
    """Test that root endpoint requires API key."""
    response = test_client.get("/_meta")

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Invalid X-Api-Key header" in response.json()["detail"]
