from asyncio import TaskGroup
from typing import Any, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Query

from ehp.db.db_manager import DBManager
from ehp.config import settings


async def get_async_page_info(
    query: Query,
    page: int = 1,
    items_per_page: int = settings.ITEMS_PER_PAGE,
    db_manager: DBManager = None,
) -> Tuple[List[Any], int, int]:
    """Get paginated results with concurrent query execution.

    Args:
        query: Base query to paginate
        page: Current page number (default: 1)
        items_per_page: Number of items per page
        db_manager: Database manager instance
    """
    async with TaskGroup() as task_group:

        async def get_count():
            async with db_manager.transaction() as session:
                return await session.scalar(
                    select(func.count()).select_from(query.subquery())
                )

        async def get_data():
            async with db_manager.transaction() as session:
                result = await session.execute(
                    query.offset(abs((page - 1) * items_per_page)).limit(
                        abs(items_per_page)
                    )
                )
                return list(result.unique().scalars().all())

        count_task = task_group.create_task(get_count())
        data_task = task_group.create_task(get_data())

    total_count = await count_task
    items = await data_task

    return items, total_count, items_per_page


def prepare_pagination_response(
    page: int = 1,
    items_per_page: int = settings.ITEMS_PER_PAGE,
    items_on_current_page: int = 1,
    total: int = 1,
) -> dict:
    total = 1 if total <= 0 else total
    items_per_page = 1 if items_per_page <= 0 else items_per_page
    return {
        "current_page": page,
        "total_pages": (total // settings.ITEMS_PER_PAGE) + 1,
        "items_per_page": items_per_page,
        "total_items": total,
        "items_on_current_page": items_on_current_page,
    }
