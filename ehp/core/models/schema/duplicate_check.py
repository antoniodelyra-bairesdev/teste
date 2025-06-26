from datetime import datetime
from typing import Optional

from ehp.utils.validation import ValidatedModel


class DuplicateCheckResponseSchema(ValidatedModel):
    """Schema for duplicate check response"""

    is_duplicate: bool
    duplicate_article_id: Optional[int] = None
    duplicate_created_at: Optional[datetime] = None
    hours_difference: Optional[float] = None
    threshold_hours: int
    message: str
