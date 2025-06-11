import logging
import time
import uuid
from contextvars import ContextVar
from typing import Annotated, Optional

from fastapi import Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ehp.base.session import SessionManager
from ehp.config import settings
from ehp.utils.base import log_error


async def get_user_session(
    request: Request, x_token_auth: Annotated[Optional[str], Header()] = None
) -> None:
    session_manager = SessionManager()
    if x_token_auth:
        token = session_manager.get_session_from_token(x_token_auth)
        if token is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid X-Token-Auth header",
            )
        if hasattr(request.state, "request_config"):
            request.state.request_config["user_session"] = token
        else:
            request.state.request_config = {"user_session": token}


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
            log_error(f"Request error: {e}")
            return JSONResponse(
                {
                    "error": "Internal server error",
                    "request_id": request.state.request_id,
                },
                status_code=500,
            )
