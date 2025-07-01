from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.paging import PagedResponse
from ehp.core.models.schema.wikiclip import (
    WikiClipResponseSchema,
    WikiClipSchema,
    WikiClipSearchSchema,
)
from ehp.core.models.schema.duplicate_check import DuplicateCheckResponseSchema
from ehp.core.repositories.wikiclip import WikiClipRepository
from ehp.core.services.session import AuthContext, get_authentication
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.base import log_error
from ehp.db.sqlalchemy_async_connector import get_db_session
from ehp.utils.constants import HTTP_INTERNAL_SERVER_ERROR


router = APIRouter(prefix="/wikiclip", tags=["wikiclip"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def save_wikiclip(
    wikiclip_data: WikiClipSchema,
    db_session: ManagedAsyncSession,
    user: AuthContext,
) -> WikiClipResponseSchema:
    """Save a new WikiClip (article) with all related data."""

    try:
        repository = WikiClipRepository(db_session)

        # We are not checking for duplicates anymore here, we are doing it in the duplicate check endpoint
        # today = date.today()
        # # Check if URL already exists
        # if await repository.exists(
        #     str(wikiclip_data.url),
        #     today,
        #     wikiclip_data.title,
        #     user.user.id,
        # ):
        #     log_error(
        #         f"WikiClip with parameters {wikiclip_data.url},"
        #         + f" {today} and {wikiclip_data.title} already exists"
        #     )
        #     raise HTTPException(
        #         status_code=409, detail="A WikiClip with this URL already exists"
        #     )

        # Create new WikiClip
        wikiclip = WikiClip(
            title=wikiclip_data.title,
            content=wikiclip_data.content,
            url=str(wikiclip_data.url),
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
            content=created_wikiclip.content,
        )

    except HTTPException:
        await db_session.rollback()
        raise
    except Exception as e:
        await db_session.rollback()
        log_error(f"Error saving WikiClip: {e}")
        raise HTTPException(status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/duplicate-check",
    response_model=DuplicateCheckResponseSchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_authentication)],
)
async def duplicate_check_endpoint(
    db_session: ManagedAsyncSession,
    user: AuthContext,
    url: str = Query(..., description="Article URL"),
    title: str = Query(..., description="Article title"),
    hours_threshold: int = Query(
        ..., ge=1, le=96, description="Time threshold in hours"
    ),
) -> DuplicateCheckResponseSchema:
    """
    Check if a user has already saved a specific article within a time threshold.

    This endpoint performs a duplicate check based on **URL**, **title**, and a configurable
    time threshold. It helps prevent users from saving the same article multiple times
    within a specified period.

    ## Parameters

    - **db_session**: Database session for repository operations
    - **user**: Authenticated user context
    - **url**: The URL of the article to check for duplicates
    - **title**: The title of the article to check for duplicates
    - **hours_threshold**: Time threshold in hours (1-96) to consider articles as duplicates

    ## Returns

    `DuplicateCheckResponseSchema` containing:

    - **is_duplicate**: Boolean indicating if a duplicate was found
    - **duplicate_article_id**: ID of the duplicate article (if found)
    - **duplicate_created_at**: Creation timestamp of the duplicate (if found)
    - **hours_difference**: Hours between current time and duplicate creation (if found)
    - **threshold_hours**: The threshold used for the check
    - **message**: Human-readable message describing the result

    ## Raises

    - `HTTPException`: 500 if an internal server error occurs during the check

    ## Example

    **Request:**
    ```
    GET /wikiclip/duplicate-check?url=https://example.com/article&title=Test&hours_threshold=24
    ```

    **Response when duplicate found:**
    ```json
    {
        "is_duplicate": true,
        "duplicate_article_id": 123,
        "duplicate_created_at": "2024-01-01T10:00:00",
        "hours_difference": 2.5,
        "threshold_hours": 24,
        "message": "Duplicate article found. Created 2.5 hours ago."
    }
    ```

    **Response when no duplicate found:**
    ```json
    {
        "is_duplicate": false,
        "duplicate_article_id": null,
        "duplicate_created_at": null,
        "hours_difference": null,
        "threshold_hours": 24,
        "message": "No duplicate found within 24 hours threshold."
    }
    ```
    """
    try:
        repository = WikiClipRepository(db_session)
        is_duplicate, duplicate_article, hours_difference = (
            await repository.check_duplicate(
                url=str(url),
                title=title,
                user_id=user.user.id,
                hours_threshold=hours_threshold,
            )
        )
        if is_duplicate:
            return DuplicateCheckResponseSchema(
                is_duplicate=True,
                duplicate_article_id=(
                    duplicate_article.id if duplicate_article else None
                ),
                duplicate_created_at=(
                    duplicate_article.created_at if duplicate_article else None
                ),
                hours_difference=(
                    round(hours_difference, 2) if hours_difference else None
                ),
                threshold_hours=hours_threshold,
                message=f"Duplicate article found. Created {round(hours_difference, 2)} hours ago.",
            )
        else:
            return DuplicateCheckResponseSchema(
                is_duplicate=False,
                duplicate_article_id=None,
                duplicate_created_at=None,
                hours_difference=None,
                threshold_hours=hours_threshold,
                message=f"No duplicate found within {hours_threshold} hours threshold.",
            )
    except Exception as e:
        log_error(f"Error in duplicate check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
        raise HTTPException(status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Could not save WikiClip due to an error")


@router.get(
    "/{wikiclip_id}",
    response_model=WikiClipResponseSchema,
    dependencies=[Depends(get_authentication)],
)
async def get_wikiclip(
    wikiclip_id: int, db_session: ManagedAsyncSession
) -> WikiClipResponseSchema:
    """Get a WikiClip by ID."""

    try:
        repository = WikiClipRepository(db_session)
        wikiclip = await repository.get_by_id_or_404(wikiclip_id)

        return WikiClipResponseSchema(
            id=wikiclip.id,
            title=wikiclip.title,
            url=wikiclip.url,
            related_links=wikiclip.related_links,
            created_at=wikiclip.created_at,
            content=wikiclip.content,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error getting WikiClip {wikiclip_id}: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Could not retrieve WikiClip due to an error"
        )


@router.get("/")
async def fetch_wikiclips(
    db_session: ManagedAsyncSession,
    user: AuthContext,
    search: Annotated[WikiClipSearchSchema, Depends()],
) -> PagedResponse[WikiClipResponseSchema, WikiClipSearchSchema]:
    """Fetch paginated WikiClips for the authenticated user."""

    try:
        repository = WikiClipRepository(db_session)
        total_count = await repository.count(user.user.id, search)
        wikiclips = await repository.search(user.user.id, search)
        return PagedResponse[WikiClipResponseSchema, WikiClipSearchSchema](
            data=[
                WikiClipResponseSchema(
                    id=wikiclip.id,
                    title=wikiclip.title,
                    url=wikiclip.url,
                    related_links=wikiclip.related_links,
                    created_at=wikiclip.created_at,
                )
                for wikiclip in wikiclips
            ],
            page=search.page,
            page_size=search.size,
            total_count=total_count,
            filters=search,
        )

    except Exception as e:
        log_error(f"Error fetching WikiClips: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Could not fetch WikiClips due to an error"
        )


@router.get(
    "/{wikiclip_id}/content",
    dependencies=[Depends(get_authentication)],
    response_class=Response,
)
async def get_wikiclip_content(
    wikiclip_id: int, db_session: Annotated[AsyncSession, Depends(get_db_session)]
) -> Response:
    """Content fetch endpoint."""

    try:
        repository = WikiClipRepository(db_session)
        wikiclip = await repository.get_by_id_or_404(wikiclip_id)

        return Response(
            content=wikiclip.content,
            media_type="text/plain",
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error getting WikiClip content {wikiclip_id}: {e}")
        raise HTTPException(status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error")
