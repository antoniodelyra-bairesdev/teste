from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Annotated, List

from fastapi import Query
from pydantic import AfterValidator, Field, HttpUrl, field_validator

from ehp.core.models.schema.paging import PagedQuery
from ehp.utils.validation import ValidatedModel, summarize_text


SUMMARY_MAX_LENGTH = 200


@AfterValidator
def _empty_string_validator(value: str) -> str:
    """Validator to ensure a string is not empty or just whitespace."""
    if not value or not value.strip():
        raise ValueError("String cannot be empty or just whitespace")
    return value.strip()


class WikiClipSchema(ValidatedModel):
    """Schema for saving wikiclip content"""

    content: Annotated[
        str, Field(description="WikiClip content"), _empty_string_validator
    ]
    title: Annotated[
        str,
        Field(description="WikiClip title", max_length=500),
        _empty_string_validator,
    ]
    # Using HttpUrl for URL validation
    # None is for non-applicable cases (e.g., files)
    url: Annotated[HttpUrl | None, Field(description="WikiClip URL", max_length=2000)]
    related_links: List[str] | None = Field(
        None, description="List of related links to the WikiClip", max_length=100
    )

    @field_validator("related_links")
    def validate_related_links(cls, v):
        if v is not None:
            for link in v:
                if not isinstance(link, str) or not link.strip():
                    raise ValueError("All related links must be non-empty strings")
        return v


class WikiClipResponseSchema(ValidatedModel):
    """Response schema for saved wikiclip"""

    id: int
    title: str
    url: HttpUrl | None  # URL is optional to support processed files
    related_links: List[str] | None = None
    created_at: datetime
    content: str | None = None
    summary: str | None = None


class WikiClipResponseWithSettings(ValidatedModel):
    """Response schema for saved wikiclip with reading settings"""

    id: int
    title: str
    url: HttpUrl
    related_links: List[str] | None = None
    created_at: datetime
    content: str | None = None
    reading_settings: dict | None = None


class SummarizedWikiclipResponseSchema(WikiClipResponseSchema):
    @field_validator("content", mode="after")
    @classmethod
    def summarize_content(cls, content: str) -> str:
        return summarize_text(content, SUMMARY_MAX_LENGTH)


class TrendingWikiClipSchema(ValidatedModel):
    """Response schema for trending wikiclips"""

    wikiclip_id: int
    title: str
    summary: str | None
    created_at: datetime


class WikiClipSearchSortStrategy(str, Enum):
    """Enum for sorting strategies in WikiClip search."""

    CREATION_DATE_ASC = "creation_date_asc"
    CREATION_DATE_DESC = "creation_date_desc"

    def __str__(self) -> str:
        """Return the string representation of the enum value."""
        return self.value


@dataclass
class WikiClipSearchSchema(PagedQuery):
    """Schema for searching WikiClips with pagination and sorting options."""

    search_term: str | None = Query(
        None,
        description="Search term to filter WikiClips by title or content",
        max_length=500,
    )
    sort_by: WikiClipSearchSortStrategy = Query(
        WikiClipSearchSortStrategy.CREATION_DATE_DESC,
        description="Sorting strategy for the search results",
    )
    created_before: datetime | None = Query(
        None,
        description="Filter WikiClips created before this date",
    )
    created_after: datetime | None = Query(
        None,
        description="Filter WikiClips created after this date",
    )
    filter_by_user: bool = Query(
        False,
        description="Filter WikiClips by user ID",
    )


class MyWikiPagesResponseSchema(ValidatedModel):
    """Response schema for user's saved pages with metadata"""

    wikiclip_id: int = Field(..., description="WikiClip unique identifier")
    title: str = Field(..., description="WikiClip title")
    url: HttpUrl = Field(..., description="WikiClip URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    content_summary: str = Field(
        ..., description="Content summary (truncated to 200 chars)"
    )
    sections_count: int = Field(default=0, description="Number of sections/parts")

    @field_validator("content_summary", mode="after")
    @classmethod
    def summarize_content_summary(cls, content_summary: str) -> str:
        return summarize_text(content_summary, SUMMARY_MAX_LENGTH)
