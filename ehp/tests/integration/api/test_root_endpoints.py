import pytest
from fastapi import FastAPI

from ehp.tests.utils.test_client import EHPTestClient


@pytest.mark.integration
@pytest.mark.usefixtures("setup_jwt")
def test_root_endpoint_integration(test_client: EHPTestClient):
    """Test the root meta endpoint with all dependencies mocked."""

    response = test_client.get("/_meta")

    assert response.status_code == 200

    result = response.json()
    assert "name" in result
    assert "version" in result
    assert "description" in result
    assert "time" in result

    # # Verify pagination info is included in response
    # assert "pagination" in response.json() # Uncomment if pagination is expected

    # Verify response metadata
    # assert "response_id" in response.json() # Uncomment if response_id is expected
    # assert "response_time" in response.json() # Uncomment if response_time is expected


@pytest.mark.integration
def test_root_endpoint_unauthorized(app: FastAPI):
    """Test the root endpoint with invalid API key."""
    client = EHPTestClient(app)

    # Override default API key with invalid one
    client.api_key = "invalid-key"

    response = client.get("/_meta")

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Invalid X-Api-Key header" in response.json()["detail"]
