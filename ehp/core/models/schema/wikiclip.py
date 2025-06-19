from datetime import datetime
from typing import Annotated, List

from pydantic import AfterValidator, Field, HttpUrl, field_validator

from ehp.utils.validation import ValidatedModel


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
    url: Annotated[HttpUrl, Field(description="WikiClip URL", max_length=2000)]
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
    url: str
    related_links: List[str] | None = None
    created_at: datetime
