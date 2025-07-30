import logging
import time
import uuid
from contextvars import ContextVar
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header, Query, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ehp.base.jwt_helper import JWTClaimsPayload
from ehp.base.session import SessionManager
from ehp.config import settings
from ehp.utils.base import log_error

auth_handler = APIKeyHeader(name="x-token-auth", auto_error=False)


def authenticated_session(
    claims: Annotated[str, Depends(auth_handler)],
) -> JWTClaimsPayload:
    """
    Dependency to get the authenticated user's claims.
    This is used to ensure that the user is authenticated for certain endpoints.
    """

    session_manager = SessionManager()
    try:
        session_data = session_manager.get_session_from_token(token=claims)
        if session_data is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )
        # Exp needs to be checked here because the get_session_from_token call does
        # not check for expiration
        return session_manager.jwt_generator.decode_token(
            session_data.session_token, verify_exp=True
        )
    except ValueError as e:
        log_error(f"Error decoding token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )


def authorized_session(
    x_token_auth: Annotated[str | None, Depends(auth_handler)],
    x_api_key: Annotated[str | None, Header()] = None,
    x_token_auth_query: Annotated[str | None, Query(alias="x-token-auth")] = None,
) -> JWTClaimsPayload | None:
    """
    Dependency to ensure proper authorization for endpoints.
    It checks for the presence of an API key or a valid JWT token in the request headers
    or query parameters. If neither is provided, it raises a 403 Forbidden error.
    """

    x_token_auth = x_token_auth or x_token_auth_query
    if x_api_key is None and x_token_auth is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
        )
    elif x_api_key is not None:
        from ehp.utils.authentication import needs_api_key
        needs_api_key(x_api_key)
    elif x_token_auth_query is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="API key is required"
        )
    if x_token_auth:
        return authenticated_session(x_token_auth)


_request_context = ContextVar("request_context", default=None)


def get_current_request() -> Optional[Request]:
    return _request_context.get()


class RequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Store request in context var
        token = _request_context.set(request)
        try:
            response = await call_next(request)
            return response
        finally:
            _request_context.reset(token)


class ValidationMiddleware(BaseHTTPMiddleware):
    """Request validation middleware"""

    def __init__(self, app, enable_logging: bool = True):
        super().__init__(app)
        self.enable_logging = enable_logging

    async def dispatch(self, request, call_next):
        # Add request ID
        request.state.request_id = str(uuid.uuid4())

        # Skip validation for certain paths
        skip_paths = {"/_meta", "/docs", "/openapi.json"}
        if request.url.path in skip_paths:
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)

            # Add headers
            response.headers["X-Request-ID"] = request.state.request_id

            # Log if enabled
            if self.enable_logging and settings.DEBUG:
                duration = time.time() - start_time
                logging.info(
                    f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
                )

            return response

        except Exception as e:
            # Import here to avoid circular import
            from ehp.base.exceptions import DBConnectionError, RedisConnectionError, RedisError
            
            if isinstance(e, DBConnectionError):
                log_error(f"Database connection error: {e}")
                return JSONResponse(
                    {"detail": "DB connection failed"},
                    status_code=500,
                    headers={"X-Request-ID": request.state.request_id}
                )
            
            if isinstance(e, RedisConnectionError):
                log_error(f"Redis connection error: {e}")
                return JSONResponse(
                    {"detail": "Redis connection failed"},
                    status_code=500,
                    headers={"X-Request-ID": request.state.request_id}
                )
            
            if isinstance(e, RedisError):
                log_error(f"Redis operation error: {e}")
                return JSONResponse(
                    {"detail": "Redis operation failed"},
                    status_code=500,
                    headers={"X-Request-ID": request.state.request_id}
                )
            
            log_error(f"Request error: {e}")
            return JSONResponse(
                {
                    "error": "Internal server error",
                    "request_id": request.state.request_id,
                },
                status_code=500,
            )
