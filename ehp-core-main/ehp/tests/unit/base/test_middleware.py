import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, Response

from ehp.base.middleware import get_user_session, get_current_request, RequestMiddleware


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_session_with_token():
    """Test get_user_session with a valid token."""
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()
    mock_request.state.request_config = {}

    # Mock session data
    session_data = {
        "session_id": "test-session-id",
        "session_info": {
            "id": 1,
            "user_name": "testuser"
        }
    }

    # Mock get_from_redis_session
    with patch("ehp.base.middleware.get_from_redis_session", return_value=session_data):
        # Call the function with a token
        await get_user_session(mock_request, "test-token")

        # Verify session was set in request config
        assert "user_session" in mock_request.state.request_config
        assert mock_request.state.request_config["user_session"] == session_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_session_no_token():
    """Test get_user_session with no token."""
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()
    mock_request.state.request_config = {}

    # Call the function with no token
    await get_user_session(mock_request, None)

    # Verify no session was set
    assert "user_session" not in mock_request.state.request_config


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_session_no_request_config():
    """Test get_user_session when request_config doesn't exist."""
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()

    # Simulate no request_config
    if hasattr(mock_request.state, "request_config"):
        delattr(mock_request.state, "request_config")

    # Mock session data
    session_data = {
        "session_id": "test-session-id",
        "session_info": {
            "id": 1,
            "user_name": "testuser"
        }
    }

    # Mock get_from_redis_session
    with patch("ehp.base.middleware.get_from_redis_session", return_value=session_data):
        # Call the function with a token
        await get_user_session(mock_request, "test-token")

        # Verify request_config was created and session was set
        assert hasattr(mock_request.state, "request_config")
        assert "user_session" in mock_request.state.request_config
        assert mock_request.state.request_config["user_session"] == session_data


@pytest.mark.unit
def test_get_current_request():
    """Test get_current_request function."""
    # Default value should be None
    assert get_current_request() is None

    # Test with a request set in context
    mock_request = MagicMock(spec=Request)

    # We need to patch _request_context.get
    with patch("ehp.base.middleware._request_context.get", return_value=mock_request):
        assert get_current_request() == mock_request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_middleware():
    """Test RequestMiddleware dispatch method."""
    middleware = RequestMiddleware()

    # Mock request and call_next
    mock_request = MagicMock(spec=Request)
    mock_response = MagicMock(spec=Response)
    mock_call_next = AsyncMock(return_value=mock_response)

    # We need to patch _request_context.set and reset
    mock_token = MagicMock()

    with patch("ehp.base.middleware._request_context.set", return_value=mock_token) as mock_set, \
            patch("ehp.base.middleware._request_context.reset") as mock_reset:
        # Call the dispatch method
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify context was set and reset
        mock_set.assert_called_once_with(mock_request)
        mock_reset.assert_called_once_with(mock_token)

        # Verify call_next was called with the request
        mock_call_next.assert_called_once_with(mock_request)

        # Verify the response was returned
        assert response == mock_response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_middleware_with_exception():
    """Test RequestMiddleware dispatch method when call_next raises an exception."""
    middleware = RequestMiddleware()

    # Mock request and call_next
    mock_request = MagicMock(spec=Request)
    mock_call_next = AsyncMock(side_effect=Exception("Test error"))

    # We need to patch _request_context.set and reset
    mock_token = MagicMock()

    with patch("ehp.base.middleware._request_context.set", return_value=mock_token) as mock_set, \
            patch("ehp.base.middleware._request_context.reset") as mock_reset:
        # Call the dispatch method, expecting an exception
        with pytest.raises(Exception) as excinfo:
            await middleware.dispatch(mock_request, mock_call_next)

        assert "Test error" in str(excinfo.value)

        # Verify context was set and reset, even with the exception
        mock_set.assert_called_once_with(mock_request)
        mock_reset.assert_called_once_with(mock_token)

        # Verify call_next was called with the request
        mock_call_next.assert_called_once_with(mock_request)
