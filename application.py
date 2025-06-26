#
# Echo Harbor Press Core Service
#
import logging
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse

from ehp.base.middleware import RequestMiddleware
from ehp.config import settings
from ehp.core.services import (
    logout_router,
    password_router,
    registration_router,
    root_router,
    token_router,
    wikiclip_router,
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

app.add_middleware(RequestMiddleware)

app.include_router(logout_router)
app.include_router(password_router)
app.include_router(registration_router)
app.include_router(root_router)
app.include_router(token_router)
app.include_router(wikiclip_router)


@app.get("/openapi.json")
async def get_open_api_endpoint() -> JSONResponse:
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
    if settings.DEBUG:
        return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
    return None
