from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from fastapi import Query
from pydantic import Field, field_validator

from ehp.core.models.schema.paging import PagedQuery
from ehp.utils.validation import ValidatedModel


class LensSortStrategy(str, Enum):
    """Enum for sorting strategies in Lens search."""

    CREATION_DATE_ASC = "creation_date_asc"
    CREATION_DATE_DESC = "creation_date_desc"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"

    def __str__(self) -> str:
        """Return the string representation of the enum value."""
        return self.value


@dataclass
class LensSearchSchema(PagedQuery):
    """Schema for searching Lenses with pagination, filtering and sorting options."""

    search_term: str | None = Query(
        None,
        description="Search term to filter Lenses by title or content",
        max_length=500,
    )
    lens_type_name: str | None = Query(
        None,
        description="Filter Lenses by lens type name (partial match)",
        max_length=100,
    )
    include_disabled: bool = Query(
        False,
        description="Include disabled lenses in the results",
    )
    sort_by: LensSortStrategy = Query(
        LensSortStrategy.CREATION_DATE_DESC,
        description="Sorting strategy for the search results",
    )

    @field_validator("search_term")
    @classmethod
    def validate_search_term(cls, v: str | None) -> str | None:
        """Validate search term is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Search term cannot be empty")
        return v.strip() if v else v

    @field_validator("lens_type_name")
    @classmethod
    def validate_lens_type_name(cls, v: str | None) -> str | None:
        """Validate lens type name is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Lens type name cannot be empty")
        return v.strip() if v else v


class LensTypeResponseSchema(ValidatedModel):
    """Response schema for LensType."""

    id: int = Field(..., description="LensType unique identifier")
    name: str = Field(..., description="LensType name")
    description: str | None = Field(None, description="LensType description")
    created_at: datetime = Field(..., description="Creation timestamp")


class LensResponseSchema(ValidatedModel):
    """Response schema for Lens."""

    id: int = Field(..., description="Lens unique identifier")
    title: str = Field(..., description="Lens title")
    content: str = Field(..., description="Lens content/prompt")
    created_at: datetime = Field(..., description="Creation timestamp")
    lens_type: LensTypeResponseSchema = Field(..., description="Associated lens type")
    disabled_at: datetime | None = Field(None, description="Disabled timestamp")
    is_active: bool = Field(..., description="Whether the lens is currently active")
