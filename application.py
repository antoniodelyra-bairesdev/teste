#
# Echo Harbor Press Core Service
#
import logging
from typing import Any

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse

from ehp.base.exceptions import default_error_handler
from ehp.base.middleware import RequestMiddleware
from ehp.config import settings
from ehp.core.services import (
    logout_router,
    password_router,
    reading_settings_router,
    registration_router,
    root_router,
    token_router,
    user_non_api_key_router,
    user_router,
    wikiclip_router,
)
from ehp.db.db_manager import DBManager, get_db_manager
from ehp.utils.authentication import needs_api_key

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    dependencies=[Depends(get_db_manager)],
)

# Create router for endpoints that require API key
keyed_router = APIRouter(dependencies=[Depends(needs_api_key)])

# Add global exception handler
app.add_exception_handler(500, default_error_handler)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request middleware for context management
app.add_middleware(RequestMiddleware)

# Reading Settings are now handled via dependency injection in endpoints

# Include routers that require API key
keyed_router.include_router(logout_router)
keyed_router.include_router(password_router)
keyed_router.include_router(reading_settings_router)
keyed_router.include_router(registration_router)
keyed_router.include_router(root_router)
keyed_router.include_router(token_router)
keyed_router.include_router(user_router)
keyed_router.include_router(wikiclip_router)

# Include routers that don't require API key
app.include_router(user_non_api_key_router)

# Include the keyed router last
app.include_router(keyed_router)


@app.get("/openapi.json")
async def get_open_api_endpoint() -> JSONResponse:
    """Get OpenAPI specification (only available in debug mode)."""
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
    """Get API documentation (only available in debug mode)."""
    if settings.DEBUG:
        return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
    return None
