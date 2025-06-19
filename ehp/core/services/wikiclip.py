from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.wikiclip import WikiClipResponseSchema, WikiClipSchema
from ehp.core.repositories.wikiclip import WikiClipRepository
from ehp.core.services.session import AuthContext, get_authentication
from ehp.db.sqlalchemy_async_connector import get_db_session
from ehp.utils.base import log_error

router = APIRouter(prefix="/wikiclip", tags=["wikiclip"])


@router.post(
    "/", response_model=WikiClipResponseSchema, status_code=status.HTTP_201_CREATED
)
async def save_wikiclip(
    wikiclip_data: WikiClipSchema,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthContext,
) -> WikiClipResponseSchema:
    """Save a new WikiClip (article) with all related data."""

    try:
        repository = WikiClipRepository(db_session)

        today = date.today()
        # Check if URL already exists
        if await repository.exists(
            str(wikiclip_data.url),
            today,
            wikiclip_data.title,
            user.user.id,
        ):
            log_error(
                f"WikiClip with parameters {wikiclip_data.url},"
                + f" {today} and {wikiclip_data.title} already exists"
            )
            raise HTTPException(
                status_code=409, detail="A WikiClip with this URL already exists"
            )

        # Create new WikiClip
        wikiclip = WikiClip(
            title=wikiclip_data.title,
            content=wikiclip_data.content,
            url=wikiclip_data.url,
            related_links=wikiclip_data.related_links,
            user_id=user.user.id,
        )

        # Save to database
        created_wikiclip = await repository.create(wikiclip)
        await db_session.commit()

        return WikiClipResponseSchema(
            id=created_wikiclip.id,
            title=created_wikiclip.title,
            url=created_wikiclip.url,
            related_links=created_wikiclip.related_links,
            created_at=created_wikiclip.created_at,
        )

    except HTTPException:
        await db_session.rollback()
        raise
    except Exception as e:
        await db_session.rollback()
        log_error(f"Error saving WikiClip: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{wikiclip_id}",
    response_model=WikiClipResponseSchema,
    dependencies=[Depends(get_authentication)],
)
async def get_wikiclip(
    wikiclip_id: int, db_session: Annotated[AsyncSession, Depends(get_db_session)]
) -> WikiClipResponseSchema:
    """Get a WikiClip by ID."""

    try:
        repository = WikiClipRepository(db_session)
        wikiclip = await repository.get_by_id(wikiclip_id)

        if not wikiclip:
            raise HTTPException(status_code=404, detail="WikiClip not found")

        return WikiClipResponseSchema(
            id=wikiclip.id,
            title=wikiclip.title,
            url=wikiclip.url,
            related_links=wikiclip.related_links,
            created_at=wikiclip.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error getting WikiClip {wikiclip_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
