import hashlib
import json
import os
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypeVar

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)

from ehp.base.redis_storage import get_redis_client
from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.duplicate_check import DuplicateCheckResponseSchema
from ehp.core.models.schema.paging import PagedQuery, PagedResponse, ResponseMetadata
from ehp.core.models.schema.wikiclip import (
    MyWikiPagesResponseSchema,
    SummarizedWikiclipResponseSchema,
    TrendingWikiClipSchema,
    WikiClipResponseSchema,
    WikiClipResponseWithSettings,
    WikiClipSchema,
    WikiClipSearchSchema,
)
from ehp.core.repositories.wikiclip import WikiClipRepository
from ehp.core.services.documents import DocumentExtractor
from ehp.core.services.session import (
    AuthContext,
    get_authentication,
    ReadingSettingsContext,
)
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.base import log_error, safe_calculate_total_pages
from ehp.utils.cache import cache_response, invalidate_user_cache
from ehp.utils.constants import HTTP_INTERNAL_SERVER_ERROR

ResponseT = TypeVar("ResponseT")
FilterT = TypeVar("FilterT", default=None)


def create_empty_paged_response(
    response_type: type[ResponseT],
    filter_type: FilterT = None,
    reading_settings: dict | None = None,
) -> PagedResponse[ResponseT, FilterT]:
    """Create an empty PagedResponse with correct empty data format."""
    return PagedResponse[response_type, filter_type](
        data=[],
        total_count=0,
        page=0,
        page_size=0,
        total_pages=0,
        has_next=False,
        has_previous=False,
        filters=None,
        metadata=(
            ResponseMetadata(reading_settings=reading_settings)
            if reading_settings is not None
            else None
        ),
    )


def generate_cache_key(
    filters: Dict[str, Any], page: int, items_per_page: int, user_id: int
) -> str:
    """Generate consistent cache key for filter combinations"""
    cache_data = {
        "filters": sorted(filters.items()),
        "page": page,
        "items_per_page": items_per_page,
        "user_id": user_id,
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return f"my_pages:{hashlib.sha256(cache_string.encode()).hexdigest()}"


def get_cached_articles(
    filters: Dict[str, Any], page: int, items_per_page: int, user_id: int
) -> Optional[Dict[str, Any]]:
    """Get cached articles for the given filters and pagination"""
    cache_key = generate_cache_key(filters, page, items_per_page, user_id)

    try:
        redis_client = get_redis_client()
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        log_error(f"Error getting cached articles: {e}")
    return None


def set_cached_articles(
    filters: Dict[str, Any],
    payload: List[Dict[str, Any]],
    total_elements: int,
    page: int,
    items_per_page: int,
    user_id: int,
) -> None:
    """Cache articles with filters and pagination info"""
    cache_key = generate_cache_key(filters, page, items_per_page, user_id)

    payload_to_cache = {
        "filters": filters,
        "payload": payload,
        "page": page,
        "items_per_page": items_per_page,
        "total_elements": total_elements,
    }

    try:
        redis_client = get_redis_client()
        # Cache for 5 minutes
        redis_client.setex(cache_key, 300, json.dumps(payload_to_cache, default=str))
    except Exception as e:
        log_error(f"Error setting cached articles: {e}")


router = APIRouter(prefix="/wikiclip", tags=["wikiclip"])


def generate_summary(content: str) -> str:
    """Generate a summary from content by taking first 100 characters and adding ellipsis."""
    # This logic must be replaced after with an AI generated summary
    if not content:
        return ""

    if len(content) <= 100:
        return content

    return content[:100] + "..."


@router.post("/", status_code=status.HTTP_201_CREATED)
async def save_wikiclip(
    wikiclip_data: WikiClipSchema,
    db_session: ManagedAsyncSession,
    user: AuthContext,
) -> WikiClipResponseSchema:
    """Save a new WikiClip (article) with all related data."""

    try:
        repository = WikiClipRepository(db_session)

        # Generate summary from content
        summary = generate_summary(wikiclip_data.content)

        # Create new WikiClip
        wikiclip = WikiClip(
            title=wikiclip_data.title,
            content=wikiclip_data.content,
            summary=summary,
            url=str(wikiclip_data.url) if wikiclip_data.url else None,
            related_links=wikiclip_data.related_links,
            user_id=user.user.id,
        )

        # Save to database
        created_wikiclip = await repository.create(wikiclip)
        await db_session.commit()

        # Invalidate trending cache for this user
        invalidate_user_cache(user.user.id, "trending")
        # Invalidate my_pages cache for this user
        invalidate_user_cache(user.user.id, "my_pages")

        return WikiClipResponseSchema(
            id=created_wikiclip.id,
            title=created_wikiclip.title,
            url=created_wikiclip.url,
            related_links=created_wikiclip.related_links,
            created_at=created_wikiclip.created_at,
            content=created_wikiclip.content,
            summary=created_wikiclip.summary,
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
async def get_my_saved_pages(
    db_session: ManagedAsyncSession,
    user: AuthContext,
    reading_settings: ReadingSettingsContext,
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    refresh: bool = Query(False, description="Bypass cache and get fresh data"),
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
        "total_pages": 1,
        "has_next": false,
        "has_previous": false,
        "filters": null
    }
    ```
    """

    try:
        items_list = []
        total_elements = 0
        items_per_page = size

        # For now, we don't have filters, but we'll create an empty dict for caching
        filters = {}

        if not refresh:
            cached_payload = get_cached_articles(
                filters, page, items_per_page, user.user.id
            )
            if cached_payload:
                items_list = cached_payload.get("payload", [])
                total_elements = cached_payload.get("total_elements", 0)

        if not items_list:
            repository = WikiClipRepository(db_session)

            # Get total count and pages for the user
            total_elements = await repository.count_user_pages(user.user.id)

            # Return empty response if no data
            if total_elements == 0:
                return create_empty_paged_response(
                    MyWikiPagesResponseSchema, reading_settings=reading_settings
                )

            wikiclips = await repository.get_user_pages(
                user.user.id, page=page, page_size=size
            )

            # Transform WikiClips to response schema
            items_list = []
            for wikiclip in wikiclips:
                # Extract tags if available (related many-to-many)
                tags = (
                    [tag.description for tag in wikiclip.tags]
                    if hasattr(wikiclip, "tags") and wikiclip.tags
                    else []
                )

                # Count sections (simple count of paragraphs/line breaks)
                sections_count = (
                    len([p for p in wikiclip.content.split("\n\n") if p.strip()])
                    if wikiclip.content
                    else 0
                )

                items_list.append(
                    {
                        "wikiclip_id": wikiclip.id,
                        "title": wikiclip.title,
                        "url": wikiclip.url,
                        "created_at": (
                            wikiclip.created_at.isoformat()
                            if wikiclip.created_at
                            else None
                        ),
                        "tags": tags,
                        "content_summary": wikiclip.summary if wikiclip.summary else "",
                        "sections_count": sections_count,
                    }
                )

            # Cache the results
            set_cached_articles(
                filters, items_list, total_elements, page, items_per_page, user.user.id
            )

        # Convert list of dicts to response schema objects
        response_data = [MyWikiPagesResponseSchema(**item) for item in items_list]

        total_pages = safe_calculate_total_pages(total_elements, size)
        return PagedResponse[MyWikiPagesResponseSchema, None](
            data=response_data,
            total_count=total_elements,
            page=page,
            page_size=size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
            filters=None,
            metadata=ResponseMetadata(reading_settings=reading_settings),
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
    reading_settings: ReadingSettingsContext,
    paging: Annotated[PagedQuery, Depends()],
) -> PagedResponse[TrendingWikiClipSchema, None]:
    """Get trending WikiClips ordered by publication date descending."""

    try:
        repository = WikiClipRepository(db_session)
        total_count = await repository.count_trending(user.user.id)

        # Return empty response if no data
        if total_count == 0:
            return create_empty_paged_response(
                TrendingWikiClipSchema, reading_settings=reading_settings
            )

        wikiclips = await repository.get_trending(
            user.user.id, page=paging.page, page_size=paging.size
        )

        total_pages = safe_calculate_total_pages(total_count, paging.size)
        return PagedResponse[TrendingWikiClipSchema, None](
            data=[
                TrendingWikiClipSchema(
                    wikiclip_id=wikiclip.id,
                    title=wikiclip.title,
                    summary=wikiclip.summary,
                    created_at=wikiclip.created_at,
                )
                for wikiclip in wikiclips
            ],
            total_count=total_count,
            page=paging.page,
            page_size=paging.size,
            total_pages=total_pages,
            has_next=paging.page < total_pages,
            has_previous=paging.page > 1,
            filters=None,
            metadata=ResponseMetadata(reading_settings=reading_settings),
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
    reading_settings: ReadingSettingsContext,
    search: Annotated[WikiClipSearchSchema, Depends()],
) -> PagedResponse[WikiClipResponseSchema, WikiClipSearchSchema]:
    """Fetch paginated WikiClips for the authenticated user."""

    try:
        repository = WikiClipRepository(db_session)
        total_count = await repository.count(user.user.id, search)

        # Return empty response if no data
        if total_count == 0:
            return create_empty_paged_response(
                WikiClipResponseSchema,
                WikiClipSearchSchema,
                reading_settings=reading_settings,
            )

        wikiclips = await repository.search(user.user.id, search)
        total_pages = safe_calculate_total_pages(total_count, search.size)
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
            total_pages=total_pages,
            has_next=search.page < total_pages,
            has_previous=search.page > 1,
            filters=search,
            metadata=ResponseMetadata(reading_settings=reading_settings),
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
    reading_settings: ReadingSettingsContext,
    search: Annotated[PagedQuery, Depends()],
) -> PagedResponse[SummarizedWikiclipResponseSchema, PagedQuery]:
    repository = WikiClipRepository(db_session)
    total_count = await repository.count_suggested(user.user.id)

    # Return empty response if no data
    if total_count == 0:
        return create_empty_paged_response(
            SummarizedWikiclipResponseSchema,
            PagedQuery,
            reading_settings=reading_settings,
        )

    wikiclips = await repository.get_suggested(user.user.id, search)

    total_pages = safe_calculate_total_pages(total_count, search.size)
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
        total_pages=total_pages,
        has_next=search.page < total_pages,
        has_previous=search.page > 1,
        filters=search,
        metadata=ResponseMetadata(reading_settings=reading_settings),
    )


@router.post("/document", status_code=status.HTTP_201_CREATED)
async def save_wikiclip_document(
    auth: AuthContext,
    db_session: ManagedAsyncSession,
    document: UploadFile,
):
    # Coverage is ignored here because the test client does not support unnamed files.
    if not document.filename:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document filename is required",
        )
    supported_extensions = list(DocumentExtractor)
    _, extension = os.path.splitext(document.filename)
    extension = extension.lower().lstrip(".")
    if extension not in supported_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported document type: {extension}. Supported types: {', '.join(supported_extensions)}",
        )

    extractor = DocumentExtractor.get_extractor(extension)
    wikiclip = extractor.extract(document.file, document.filename)
    return await save_wikiclip(wikiclip, db_session, auth)


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
    response_model=WikiClipResponseWithSettings,
    dependencies=[Depends(get_authentication)],
)
async def get_wikiclip(
    wikiclip_id: int,
    db_session: ManagedAsyncSession,
    user: AuthContext,
    reading_settings: ReadingSettingsContext,
) -> WikiClipResponseWithSettings:
    """Get a WikiClip by ID."""

    try:
        repository = WikiClipRepository(db_session)
        wikiclip = await repository.get_by_id_or_404(wikiclip_id)

        return WikiClipResponseWithSettings(
            id=wikiclip.id,
            title=wikiclip.title,
            url=wikiclip.url,
            related_links=wikiclip.related_links,
            created_at=wikiclip.created_at,
            content=wikiclip.content,
            reading_settings=reading_settings,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error getting WikiClip {wikiclip_id}: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve WikiClip due to an error",
        )
