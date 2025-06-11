from typing import Optional

from .paging import PageModel


class SearchSchema(PageModel):
    search_term: Optional[str] = None
    type: Optional[str] = None


class IndexSchema(PageModel):
    index_type: str
    clean_index: bool = False
