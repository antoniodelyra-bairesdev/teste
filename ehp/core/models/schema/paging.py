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


class PagedResponse(BaseModel, Generic[T, S]):
    data: list[T]
    total_count: int
    page: int
    page_size: int
    filters: S | None = None


@dataclass
class PagedQuery:
    page: int = Query(1, ge=1, description="Page number, starting from 1")
    size: int = Query(
        settings.ITEMS_PER_PAGE,
        ge=1,
        le=settings.MAX_ITEMS_PER_PAGE,
        description="Number of items per page",
    )
