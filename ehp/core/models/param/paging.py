from typing import Optional

from pydantic import BaseModel

from ehp.config import settings


class PageModel(BaseModel):
    page: int = 1
    size: int = settings.ITEMS_PER_PAGE
    total_count: Optional[int] = None
    auth_id: Optional[int] = None
