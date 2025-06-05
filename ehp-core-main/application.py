#
# Echo Harbor Press Core Service
#
import logging
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse

from ehp.base.middleware import RequestMiddleware
from ehp.config import settings
from ehp.core.services import (
    # auth_router,
    # logout_router,
    # registration_router,
    root_router,
)
from ehp.db.db_manager import get_db_manager
from ehp.utils.authentication import needs_api_key


logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    dependencies=[Depends(needs_api_key), Depends(get_db_manager)],
)

# app.include_router(auth_router)
# app.include_router(logout_router)
# app.include_router(registration_router)
app.include_router(root_router)

app.add_middleware(RequestMiddleware)


@app.middleware("http")
async def process_after_request(request: Request, call_next: Any) -> Any:
    response = await call_next(request)

    # Access the configuration information set in the request state.
    request_config = getattr(request.state, "request_config", None)
    if request_config:
        db_session = request_config.get("db_session")
        if db_session:
            db_session.close()

    return response


@app.get("/openapi.json")
async def get_open_api_endpoint() -> JSONResponse:
    # auth: str = Depends(needs_api_key)
    if settings.DEBUG:
        return JSONResponse(
            get_openapi(
                title="FastAPI", version=settings.APP_VERSION, routes=app.routes
            )
        )
    return JSONResponse(
        content={"error": "OpenAPI documentation is not available in production."},
        status_code=404,
    )


@app.get("/docs")
@app.get("/redoc")
async def get_documentation() -> Any:
    # auth: str = Depends(needs_api_key)
    if settings.DEBUG:
        return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
    return None
