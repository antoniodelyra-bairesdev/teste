from ehp.config import settings
from ehp.core.models.db import Activity
from ehp.utils.search import clean_index, index_content, index_update_content


async def reindex_activity(should_clean_index: bool) -> None:
    if should_clean_index:
        clean_index("activity")

    total_count = await Activity.count_active()
    total_pages = (total_count // settings.ITEMS_PER_PAGE) + 1

    for page in range(1, total_pages + 1):
        activities, total_count, _ = await Activity.list_active_paged(page)
        for activity in activities:
            payload = {
                "id": activity.id,
                "activity_name": activity.name,
                "house_name": activity.house.name,
                "character_name": activity.character.name,
                "category_id": activity.category_id,
                "category_name": activity.category.name,
                "index_type": "activity",
            }
            if should_clean_index:
                index_content(payload)
            else:
                index_update_content(payload)
