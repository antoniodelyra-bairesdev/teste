from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ehp.core.models.schema.lens import (
    LensResponseSchema,
    LensSearchSchema,
)
from ehp.core.models.schema.paging import PagedResponse, ResponseMetadata
from ehp.core.repositories.lens import LensRepository
from ehp.core.services.session import ReadingSettingsContext, get_authentication
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.authentication import needs_api_key
from ehp.utils.base import log_error, safe_calculate_total_pages

router = APIRouter(
    prefix="/admin/lens",
    tags=["Lens Management"],
    dependencies=[Depends(needs_api_key)],
    responses={404: {"description": "Not found"}},
)


def create_empty_paged_response(
    reading_settings: dict | None = None,
) -> PagedResponse[LensResponseSchema, LensSearchSchema]:
    """Create an empty PagedResponse for when no lenses are found."""
    return PagedResponse[LensResponseSchema, LensSearchSchema](
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


def convert_lens_to_response(lens) -> LensResponseSchema:
    """Convert a Lens model to LensResponseSchema."""
    return LensResponseSchema(
        id=lens.id,
        title=lens.title,
        content=lens.content,
        created_at=lens.created_at,
        lens_type={
            "id": lens.lens_type.id,
            "name": lens.lens_type.name,
            "description": lens.lens_type.description,
            "created_at": lens.lens_type.created_at,
        },
        disabled_at=lens.disabled_at,
        is_active=lens.disabled_at is None,
    )


@router.get(
    "/",
    dependencies=[Depends(get_authentication)],
)
async def get_lens_list(
    db_session: ManagedAsyncSession,
    reading_settings: ReadingSettingsContext,
    search: Annotated[LensSearchSchema, Depends()],
) -> PagedResponse[LensResponseSchema, LensSearchSchema]:
    """
    Get paginated list of lenses with search and filtering capabilities.

    This endpoint retrieves a paginated list of lenses with support for:
    - Text search in title and content
    - Filtering by lens type name
    - Including/excluding disabled lenses
    - Sorting by creation date or title

    ## Parameters

    - **search_term**: Optional text to search in lens title and content
    - **lens_type_name**: Optional filter by lens type name (partial match)
    - **include_disabled**: Whether to include disabled lenses (default: false)
    - **sort_by**: Sorting strategy (creation_date_desc, creation_date_asc, title_asc, title_desc)
    - **page**: Page number for pagination (starts from 1)
    - **size**: Number of items per page

    ## Returns

    `PagedResponse[LensResponseSchema, LensSearchSchema]` containing:

    - **data**: List of lenses with full content
    - **total_count**: Total number of lenses matching the criteria
    - **page**: Current page number
    - **page_size**: Number of items per page
    - **total_pages**: Total number of pages
    - **has_next**: Whether there are more pages
    - **has_previous**: Whether there are previous pages
    - **filters**: The search criteria used
    - **metadata**: Additional response metadata including reading settings

    ## Example

    **Request:**
    ```
    GET /admin/lens/?search_term=analysis&lens_type_name=prompt&page=1&size=10
    ```

    **Response:**
    ```json
    {
        "data": [
            {
                "id": 1,
                "title": "Content Analysis Lens",
                "content": "This lens analyzes content for sentiment and key themes...",
                "created_at": "2024-01-01T10:00:00",
                "lens_type": {
                    "id": 1,
                    "name": "Analysis Prompt",
                    "description": "Content analysis lenses",
                    "created_at": "2024-01-01T09:00:00"
                },
                "disabled_at": null,
                "is_active": true
            }
        ],
        "total_count": 15,
        "page": 1,
        "page_size": 10,
        "total_pages": 2,
        "has_next": true,
        "has_previous": false,
        "filters": {
            "search_term": "analysis",
            "lens_type_name": "prompt",
            "include_disabled": false,
            "sort_by": "creation_date_desc",
            "page": 1,
            "size": 10
        },
        "metadata": {
            "reading_settings": {...}
        }
    }
    ```

    ## Raises

    - `HTTPException`: 500 if an internal server error occurs during retrieval
    """
    try:
        repository = LensRepository(db_session)

        # Get total count
        total_count = await repository.count(search)

        # Return empty response if no data
        if total_count == 0:
            return create_empty_paged_response(reading_settings=reading_settings)

        # Get lenses
        lenses = await repository.search(search)

        # Convert to response schemas
        lens_responses = [convert_lens_to_response(lens) for lens in lenses]

        # Calculate pagination info
        total_pages = safe_calculate_total_pages(total_count, search.size)

        return PagedResponse[LensResponseSchema, LensSearchSchema](
            data=lens_responses,
            total_count=total_count,
            page=search.page,
            page_size=search.size,
            total_pages=total_pages,
            has_next=search.page < total_pages,
            has_previous=search.page > 1,
            filters=search,
            metadata=ResponseMetadata(reading_settings=reading_settings),
        )

    except Exception as e:
        log_error(f"Error fetching lenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch lenses due to an error",
        )


@router.get(
    "/{lens_id}",
    dependencies=[Depends(get_authentication)],
)
async def get_lens(
    lens_id: int,
    db_session: ManagedAsyncSession,
    reading_settings: ReadingSettingsContext,
) -> LensResponseSchema:
    """
    Get a specific lens by ID with full content.

    This endpoint retrieves a single lens with complete information including
    the full content and associated lens type details.

    ## Parameters

    - **lens_id**: The unique identifier of the lens

    ## Returns

    `LensResponseSchema` containing the complete lens information

    ## Raises

    - `HTTPException`: 404 if lens is not found
    - `HTTPException`: 500 if an internal server error occurs
    """
    try:
        repository = LensRepository(db_session)
        lens = await repository.get_by_id_with_type(lens_id)

        if not lens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lens not found",
            )

        return LensResponseSchema(
            id=lens.id,
            title=lens.title,
            content=lens.content,
            created_at=lens.created_at,
            lens_type={
                "id": lens.lens_type.id,
                "name": lens.lens_type.name,
                "description": lens.lens_type.description,
                "created_at": lens.lens_type.created_at,
            },
            disabled_at=lens.disabled_at,
            is_active=lens.disabled_at is None,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error getting lens {lens_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve lens due to an error",
        )
