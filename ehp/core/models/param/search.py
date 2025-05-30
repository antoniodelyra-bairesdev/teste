from typing import Optional

from .paging import PageModel


class SearchParam(PageModel):
    search_term: Optional[str] = None
    type: Optional[str] = None


class IndexParam(PageModel):
    index_type: str
    clean_index: bool = False
