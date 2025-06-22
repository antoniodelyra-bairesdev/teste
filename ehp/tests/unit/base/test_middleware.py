from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

from ehp.base.middleware import RequestMiddleware, get_current_request


@pytest.mark.unit
def test_get_current_request():
    """Test get_current_request function."""
    # Default value should be None
    assert get_current_request() is None

    from ehp.base.middleware import _request_context

    # Test with a request set in context
    mock_request = MagicMock(spec=Request)
    _request_context.set(mock_request)

    # We need to patch _request_context.get
    assert get_current_request() == mock_request


@pytest.mark.skip(reason="Test is currently not applicable")
@pytest.mark.unit

async def test_request_middleware(test_client: TestClient):
    """Test RequestMiddleware dispatch method."""
    middleware = RequestMiddleware(test_client.app)

    # Mock request and call_next
    mock_request = MagicMock(spec=Request)
    mock_response = MagicMock(spec=Response)
    mock_call_next = AsyncMock(return_value=mock_response)

    # We need to patch _request_context.set and reset
    mock_token = MagicMock()

    with patch(
        "ehp.base.middleware._request_context.set", return_value=mock_token
    ) as mock_set, patch("ehp.base.middleware._request_context.reset") as mock_reset:
        # Call the dispatch method
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify context was set and reset
        mock_set.assert_called_once_with(mock_request)
        mock_reset.assert_called_once_with(mock_token)

        # Verify call_next was called with the request
        mock_call_next.assert_called_once_with(mock_request)

        # Verify the response was returned
        assert response == mock_response


@pytest.mark.skip(reason="Test is currently not applicable")
@pytest.mark.unit

async def test_request_middleware_with_exception(test_client: TestClient):
    """Test RequestMiddleware dispatch method when call_next raises an exception."""
    middleware = RequestMiddleware(test_client.app)

    # Mock request and call_next
    mock_request = MagicMock(spec=Request)
    mock_call_next = AsyncMock(side_effect=Exception("Test error"))

    # We need to patch _request_context.set and reset
    mock_token = MagicMock()

    with patch(
        "ehp.base.middleware._request_context.set", return_value=mock_token
    ) as mock_set, patch("ehp.base.middleware._request_context.reset") as mock_reset:
        # Call the dispatch method, expecting an exception
        with pytest.raises(Exception) as excinfo:
            await middleware.dispatch(mock_request, mock_call_next)

        assert "Test error" in str(excinfo.value)

        # Verify context was set and reset, even with the exception
        mock_set.assert_called_once_with(mock_request)
        mock_reset.assert_called_once_with(mock_token)

        # Verify call_next was called with the request
        mock_call_next.assert_called_once_with(mock_request)
