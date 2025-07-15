from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.duplicate_check import DuplicateCheckResponseSchema
from ehp.core.models.schema.paging import PagedQuery, PagedResponse
from ehp.core.models.schema.wikiclip import (
    MyWikiPagesResponseSchema,
    SummarizedWikiclipResponseSchema,
    TrendingWikiClipSchema,
    WikiClipResponseSchema,
    WikiClipSchema,
    WikiClipSearchSchema,
)
from ehp.core.repositories.wikiclip import WikiClipRepository
from ehp.core.services.session import AuthContext, get_authentication
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.base import log_error
from ehp.utils.cache import cache_response, invalidate_user_cache
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

        # Invalidate trending cache for this user
        invalidate_user_cache(user.user.id, "trending")

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
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


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
        (
            is_duplicate,
            duplicate_article,
            hours_difference,
        ) = await repository.check_duplicate(
            url=str(url),
            title=title,
            user_id=user.user.id,
            hours_threshold=hours_threshold,
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


@router.get(
    "/my",
    dependencies=[Depends(get_authentication)],
)
@cache_response("my_pages", ttl=300)
async def get_my_saved_pages(
    db_session: ManagedAsyncSession,
    user: AuthContext,
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
) -> PagedResponse[MyWikiPagesResponseSchema, None]:
    """
    Get user's saved WikiClip pages with metadata and pagination.

    This endpoint retrieves a paginated list of WikiClips saved by the authenticated user,
    including metadata such as tags, content summaries, and section counts.

    ## Parameters

    - **page**: Page number for pagination (starts from 1)
    - **size**: Number of items per page (1-100)

    ## Returns

    `PagedResponse[MyWikiPagesResponseSchema, None]` containing:

    - **data**: List of `MyWikiPagesResponseSchema` objects with:
        - **wikiclip_id**: Unique identifier of the WikiClip
        - **title**: WikiClip title
        - **url**: WikiClip URL
        - **created_at**: Creation timestamp
        - **tags**: List of associated tags
        - **content_summary**: Truncated content summary (max 200 chars)
        - **sections_count**: Number of sections/paragraphs
    - **total_count**: Total number of saved pages for the user
    - **page**: Current page number
    - **page_size**: Number of items per page
    - **filters**: None (no filters applied)

    ## Raises

    - `HTTPException`: 500 if an internal server error occurs during retrieval

    ## Example

    **Request:**
    ```
    GET /wikiclip/my?page=1&size=20
    ```

    **Response:**
    ```json
    {
        "data": [
            {
                "wikiclip_id": 123,
                "title": "Example Article",
                "url": "https://example.com/article",
                "created_at": "2024-01-01T10:00:00",
                "tags": ["technology", "programming"],
                "content_summary": "This is a summary of the article content...",
                "sections_count": 5
            }
        ],
        "total_count": 50,
        "page": 1,
        "page_size": 20,
        "filters": null
    }
    ```
    """

    try:
        repository = WikiClipRepository(db_session)

        # Get total count and pages for the user
        total_count = await repository.count_user_pages(user.user.id)
        wikiclips = await repository.get_user_pages(
            user.user.id, page=page, page_size=size
        )

        # Transform WikiClips to response schema
        response_data = []
        for wikiclip in wikiclips:
            # Extract tags if available (related many-to-many)
            tags = (
                [tag.description for tag in wikiclip.tags]
                if hasattr(wikiclip, "tags") and wikiclip.tags
                else []
            )

            # Content summary will be automatically truncated by the schema validator

            # Count sections (simple count of paragraphs/line breaks)
            sections_count = (
                len([p for p in wikiclip.content.split("\n\n") if p.strip()])
                if wikiclip.content
                else 0
            )

            response_data.append(
                MyWikiPagesResponseSchema(
                    wikiclip_id=wikiclip.id,
                    title=wikiclip.title,
                    url=wikiclip.url,
                    created_at=wikiclip.created_at,
                    tags=tags,
                    content_summary=wikiclip.content,
                    sections_count=sections_count,
                )
            )

        return PagedResponse[MyWikiPagesResponseSchema, None](
            data=response_data,
            total_count=total_count,
            page=page,
            page_size=size,
            filters=None,
        )

    except Exception as e:
        log_error(f"Error fetching user's saved pages: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail="Could not fetch saved pages due to an error",
        )


@router.get(
    "/trending",
    dependencies=[Depends(get_authentication)],
)
@cache_response("trending", ttl=300)
async def get_trending_wikiclips(
    db_session: ManagedAsyncSession,
    user: AuthContext,
    paging: Annotated[PagedQuery, Depends()],
) -> PagedResponse[TrendingWikiClipSchema, None]:
    """Get trending WikiClips ordered by publication date descending."""

    try:
        repository = WikiClipRepository(db_session)
        total_count = await repository.count_trending(user.user.id)
        wikiclips = await repository.get_trending(
            user.user.id, page=paging.page, page_size=paging.size
        )

        return PagedResponse[TrendingWikiClipSchema, None](
            data=[
                TrendingWikiClipSchema(
                    wikiclip_id=wikiclip.id,
                    title=wikiclip.title,
                    summary=wikiclip.content,
                    created_at=wikiclip.created_at,
                )
                for wikiclip in wikiclips
            ],
            total_count=total_count,
            page=paging.page,
            page_size=paging.size,
            filters=None,
        )

    except Exception as e:
        log_error(f"Error fetching trending WikiClips: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail="Could not fetch trending WikiClips due to an error",
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
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail="Could not fetch WikiClips due to an error",
        )


@router.get("/suggested")
async def get_suggested_wikiclips(
    user: AuthContext,
    db_session: ManagedAsyncSession,
    search: Annotated[PagedQuery, Depends()],
) -> PagedResponse[SummarizedWikiclipResponseSchema, PagedQuery]:
    repository = WikiClipRepository(db_session)
    total_count = await repository.count_suggested(user.user.id)
    wikiclips = await repository.get_suggested(user.user.id, search)

    return PagedResponse[SummarizedWikiclipResponseSchema, PagedQuery](
        data=[
            SummarizedWikiclipResponseSchema(
                id=wikiclip.id,
                title=wikiclip.title,
                url=wikiclip.url,
                related_links=wikiclip.related_links,
                created_at=wikiclip.created_at,
                content=wikiclip.content,
            )
            for wikiclip in wikiclips
        ],
        total_count=total_count,
        page=search.page,
        page_size=search.size,
        filters=search,
    )


@router.get(
    "/{wikiclip_id}/content",
    dependencies=[Depends(get_authentication)],
    response_class=Response,
)
async def get_wikiclip_content(
    wikiclip_id: int,
    db_session: ManagedAsyncSession,
) -> Response:
    """Content fetch endpoint."""

    try:
        repository = WikiClipRepository(db_session)
        wikiclip = await repository.get_by_id_or_404(wikiclip_id)

        return Response(
            content=wikiclip.content,
            media_type="text/plain",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error getting WikiClip content {wikiclip_id}: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


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
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve WikiClip due to an error",
        )
