from dataclasses import dataclass
from typing import Generic, Optional

from fastapi import Query
from pydantic import BaseModel
from typing_extensions import TypeVar

from ehp.config import settings

T = TypeVar("T")
S = TypeVar("S", default=None)


class PageModel(BaseModel):
    page: int = 1
    size: int = settings.ITEMS_PER_PAGE
    total_count: Optional[int] = None
    auth_id: Optional[int] = None


class ResponseMetadata(BaseModel):
    """Metadata for API responses including reading settings."""
    reading_settings: Optional[dict] = None


class PagedResponse(BaseModel, Generic[T, S]):
    data: list[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    filters: S | None = None
    metadata: Optional[ResponseMetadata] = None


@dataclass
class PagedQuery:
    page: int = Query(1, ge=1, description="Page number, starting from 1")
    size: int = Query(
        settings.ITEMS_PER_PAGE,
        ge=1,
        le=settings.MAX_ITEMS_PER_PAGE,
        description="Number of items per page",
    )
