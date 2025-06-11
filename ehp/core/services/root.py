from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ehp.config import settings

router = APIRouter(responses={404: {"description": "Not found"}})


@router.get("/_meta", response_class=JSONResponse)
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "name": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "version": settings.APP_VERSION,
            "time": settings.DEPLOYED_AT,
        }
    )
