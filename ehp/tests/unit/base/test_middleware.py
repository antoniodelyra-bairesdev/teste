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


@pytest.mark.unit
class TestValidationMiddlewareConnectionErrors:
    """Test connection error handling in ValidationMiddleware"""

    async def test_validation_middleware_db_connection_error(self):
        """Test that ValidationMiddleware handles DBConnectionError correctly. Tests lines 130-131-133-134-135-136-137-138-139."""
        from ehp.base.exceptions import DBConnectionError
        from ehp.base.middleware import ValidationMiddleware
        
        middleware = ValidationMiddleware(MagicMock())
        
        # Mock request
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.url.path = "/test"
        
        # Mock call_next to raise DBConnectionError
        async def mock_call_next(request):
            raise DBConnectionError("DB connection failed")
        
        with patch("ehp.base.middleware.log_error") as mock_log:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify response structure
            assert response.status_code == 500
            # The request_id should be set by the middleware (UUID format)
            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) > 0
            
            # Verify response body
            import json
            body = json.loads(response.body.decode())
            assert body["detail"] == "DB connection failed"
            
            # Verify log was called
            mock_log.assert_called_once()
            assert "Database connection error" in mock_log.call_args[0][0]

    async def test_validation_middleware_redis_connection_error(self):
        """Test that ValidationMiddleware handles RedisConnectionError correctly. Tests lines 130-131-141-142-143-144-145-146-147."""
        from ehp.base.exceptions import RedisConnectionError
        from ehp.base.middleware import ValidationMiddleware
        
        middleware = ValidationMiddleware(MagicMock())
        
        # Mock request
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.url.path = "/test"
        
        # Mock call_next to raise RedisConnectionError
        async def mock_call_next(request):
            raise RedisConnectionError("Redis connection failed")
        
        with patch("ehp.base.middleware.log_error") as mock_log:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify response structure
            assert response.status_code == 500
            # The request_id should be set by the middleware (UUID format)
            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) > 0
            
            # Verify response body
            import json
            body = json.loads(response.body.decode())
            assert body["detail"] == "Redis connection failed"
            
            # Verify log was called
            mock_log.assert_called_once()
            assert "Redis connection error" in mock_log.call_args[0][0]

    async def test_validation_middleware_redis_error(self):
        """Test that ValidationMiddleware handles RedisError correctly. Tests lines 130-131-149-150-151-152-153-154-155."""
        from ehp.base.exceptions import RedisError
        from ehp.base.middleware import ValidationMiddleware
        
        middleware = ValidationMiddleware(MagicMock())
        
        # Mock request
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.url.path = "/test"
        
        # Mock call_next to raise RedisError
        async def mock_call_next(request):
            raise RedisError("Redis operation failed")
        
        with patch("ehp.base.middleware.log_error") as mock_log:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify response structure
            assert response.status_code == 500
            # The request_id should be set by the middleware (UUID format)
            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) > 0
            
            # Verify response body
            import json
            body = json.loads(response.body.decode())
            assert body["detail"] == "Redis operation failed"
            
            # Verify log was called
            mock_log.assert_called_once()
            assert "Redis operation error" in mock_log.call_args[0][0]

    async def test_validation_middleware_dynamic_imports(self):
        """Test that the middleware properly imports exceptions dynamically to avoid circular imports. Tests lines 130-131."""
        from ehp.base.middleware import ValidationMiddleware
        
        middleware = ValidationMiddleware(MagicMock())
        
        # Mock request
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.url.path = "/test"
        
        # Mock call_next to raise a generic Exception (should not match any custom handlers)
        async def mock_call_next(request):
            raise Exception("Generic error")
        
        with patch("ehp.base.middleware.log_error") as mock_log:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify it falls through to generic error handling
            assert response.status_code == 500
            mock_log.assert_called()
            assert "Request error" in mock_log.call_args[0][0]

    async def test_validation_middleware_non_skip_path_with_error(self):
        """Test that error handling works for non-skip paths. Skip paths are handled differently and return early."""
        from ehp.base.exceptions import DBConnectionError
        from ehp.base.middleware import ValidationMiddleware
        
        middleware = ValidationMiddleware(MagicMock())
        
        # Mock request with non-skip path
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.url.path = "/api/test"  # Use a non-skip path
        
        # Mock call_next to raise DBConnectionError
        async def mock_call_next(request):
            raise DBConnectionError("DB connection failed")
        
        with patch("ehp.base.middleware.log_error") as mock_log:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify the error is handled properly
            assert response.status_code == 500
            # The request_id should be set by the middleware (UUID format)
            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) > 0
            
            # Verify response body
            import json
            body = json.loads(response.body.decode())
            assert body["detail"] == "DB connection failed"
            
            mock_log.assert_called_once()
            assert "Database connection error" in mock_log.call_args[0][0]