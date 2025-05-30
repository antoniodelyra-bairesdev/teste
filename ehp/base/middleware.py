from contextvars import ContextVar
from typing import Annotated, Optional

from fastapi import Header, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ehp.base.session import get_from_redis_session


async def get_user_session(
    request: Request, x_token_auth: Annotated[Optional[str], Header()]
) -> None:
    if x_token_auth:
        if hasattr(request.state, "request_config"):
            request.state.request_config["user_session"] = get_from_redis_session(
                x_token_auth
            )
        else:
            request.state.request_config = {
                "user_session": get_from_redis_session(x_token_auth)
            }


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
