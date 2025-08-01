from datetime import date, datetime, timedelta
from typing import List, Optional, TypeVar, Tuple

from fastapi import HTTPException
from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.paging import PagedQuery
from ehp.core.models.schema.wikiclip import (
    WikiClipSearchSchema,
    WikiClipSearchSortStrategy,
)
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_debug, log_error
from ehp.utils.date_utils import timezone_now
from ehp.utils.constants import HTTP_NOT_FOUND
from ehp.utils.query_timeout import with_query_timeout, safe_page_size

SelectT = TypeVar("SelectT", bound=Select)


class WikiClipRepository(BaseRepository[WikiClip]):
    """Repository for WikiClip operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, WikiClip)

    async def get_by_id_or_404(self, wikiclip_id: int) -> WikiClip:
        """Get WikiClip by ID or raise 404 HTTPException if not found."""
        wikiclip = await self.get_by_id(wikiclip_id)
        if not wikiclip:
            raise HTTPException(status_code=HTTP_NOT_FOUND, detail="WikiClip not found")
        return wikiclip

    async def exists(
        self, url: str, created_at: date, title: str, user_id: int
    ) -> bool:
        try:
            statement = select(
                exists().where(
                    and_(
                        WikiClip.url == url,
                        func.date(WikiClip.created_at) == created_at,
                        WikiClip.title == title,
                        WikiClip.user_id == user_id,
                    )
                )
            )
            result = await with_query_timeout(
                self.session.execute(statement)
            )
            exists_result = result.scalar_one()
            if not exists_result:
                log_debug(
                    f"No WikiClip exists for URL: {url}, date: {created_at}, title: {title}"
                )
            return exists_result
        except Exception as e:
            log_error(
                "Error checking if WikiClip exists for URL "
                + f"{url}, date {created_at}, title {title} and {user_id}: {e}"
            )
            return False

    def apply_filters(
        self,
        query: SelectT,
        search: WikiClipSearchSchema,
        user_id: int,
        apply_order: bool = True,
    ) -> SelectT:
        """Apply filters to the query based on search parameters."""
        query = query.where(WikiClip.user_id == user_id)
        if search.search_term:
            query = query.where(
                or_(
                    WikiClip.title.ilike(f"%{search.search_term}%"),
                    WikiClip.content.ilike(f"%{search.search_term}%"),
                )
            )
        if search.created_before:
            query = query.where(WikiClip.created_at <= search.created_before)
        if search.created_after:
            query = query.where(WikiClip.created_at >= search.created_after)
        if not apply_order:
            return query
        if search.sort_by is WikiClipSearchSortStrategy.CREATION_DATE_ASC:
            query = query.order_by(WikiClip.created_at.asc())
        elif search.sort_by is WikiClipSearchSortStrategy.CREATION_DATE_DESC:
            query = query.order_by(WikiClip.created_at.desc())
        return query

    async def search(
        self, user_id: int, search: WikiClipSearchSchema
    ) -> List[WikiClip]:
        """Search for WikiClips based on user ID and search parameters."""
        try:
            # Ensure safe page size
            safe_size = safe_page_size(search.size)
            query = select(WikiClip)
            query = self.apply_filters(query, search, user_id)
            result = await with_query_timeout(
                self.session.execute(
                    query.limit(safe_size).offset((search.page - 1) * safe_size)
                )
            )
            return list(result.scalars().unique().all())
        except Exception as e:
            log_error(f"Error searching WikiClips: {e}")
            return []

    async def count(self, user_id: int, search: WikiClipSearchSchema) -> int:
        """Count WikiClips based on user ID and search parameters."""
        try:
            query = select(func.count(WikiClip.id))
            query = self.apply_filters(query, search, user_id, apply_order=False)
            result = await with_query_timeout(
                self.session.execute(query)
            )
            return result.scalar_one()
        except Exception as e:
            log_error(f"Error counting WikiClips: {e}")
            return 0

    async def count_suggested(self, user_id: int) -> int:
        try:
            statement = select(func.count(WikiClip.id)).where(
                WikiClip.user_id == user_id
            )
            result = await with_query_timeout(
                self.session.execute(statement)
            )
            return result.scalar_one()
        except Exception:
            log_error(f"Error counting suggested wikiclips for user: {user_id}")
            return 0

    async def get_suggested(self, user_id: int, search: PagedQuery) -> List[WikiClip]:
        try:
            # Ensure safe page size
            safe_size = safe_page_size(search.size)
            query = select(WikiClip).where(WikiClip.user_id == user_id)
            result = await with_query_timeout(
                self.session.execute(
                    query.limit(safe_size).offset((search.page - 1) * safe_size)
                )
            )
            return list(result.scalars().unique().all())
        except Exception as e:
            log_error(f"Error searching WikiClips: {e}")
            return []

    async def check_duplicate(
        self, url: str, title: str, user_id: int, hours_threshold: int = 24
    ) -> Tuple[bool, Optional[WikiClip], Optional[float]]:
        """
        Check if a duplicate article exists based on URL + title + datetime threshold.

        Args:
            url: Article URL
            title: Article title
            user_id: User ID
            hours_threshold: Hours threshold for duplicate detection (1-24)

        Returns:
            Tuple of (is_duplicate, duplicate_article, hours_difference)
        """
        try:
            # Calculate the threshold datetime
            threshold_datetime = timezone_now() - timedelta(hours=hours_threshold)

            # Find existing article with same URL and title for the user
            statement = (
                select(WikiClip)
                .where(
                    and_(
                        WikiClip.url == url,
                        WikiClip.title == title,
                        WikiClip.user_id == user_id,
                        WikiClip.created_at > threshold_datetime,
                    )
                )
                .order_by(WikiClip.created_at.desc())
            )

            result = await with_query_timeout(
                self.session.execute(statement)
            )
            duplicate_article = result.scalars().first()

            if duplicate_article:
                # Calculate hours difference
                hours_diff = (
                    timezone_now() - duplicate_article.created_at
                ).total_seconds() / 3600
                log_debug(
                    f"Duplicate found for URL: {url}, title: {title}, hours diff: {hours_diff}"
                )
                return True, duplicate_article, hours_diff
            else:
                log_debug(f"No duplicate found for URL: {url}, title: {title}")
                return False, None, None

        except Exception as e:
            log_error(f"Error checking duplicate for URL {url}, title {title}: {e}")
            return False, None, None

    async def get_user_pages(self, user_id: int, page: int = 1, page_size: int = 20) -> list[WikiClip]:
        """Get user's saved pages with metadata, ordered by creation date desc."""
        try:
            # Ensure safe page size
            safe_size = safe_page_size(page_size)
            offset = (page - 1) * safe_size
            query = (
                select(WikiClip)
                .where(WikiClip.user_id == user_id)
                .order_by(WikiClip.created_at.desc())
                .limit(safe_size)
                .offset(offset)
            )
            result = await with_query_timeout(
                self.session.execute(query)
            )
            return list(result.scalars().unique().all())
        except Exception as e:
            log_error(f"Error fetching user pages for user {user_id}: {e}")
            return []

    async def count_user_pages(self, user_id: int) -> int:
        """Count total saved pages for a specific user."""
        try:
            query = select(func.count(WikiClip.id)).where(WikiClip.user_id == user_id)
            result = await with_query_timeout(
                self.session.execute(query)
            )
            return result.scalar_one()
        except Exception as e:
            log_error(f"Error counting user pages for user {user_id}: {e}")
            return 0

    async def get_trending(self, user_id: int, page: int = 1, page_size: int = 5) -> list[WikiClip]:
        """Get trending WikiClips for a specific user ordered by publication date (created_at) descending."""
        try:
            # Ensure safe page size
            safe_size = safe_page_size(page_size)
            offset = (page - 1) * safe_size
            query = (
                select(WikiClip)
                .where(WikiClip.user_id == user_id)
                .order_by(WikiClip.created_at.desc())
                .limit(safe_size)
                .offset(offset)
            )
            result = await with_query_timeout(
                self.session.execute(query)
            )
            return list(result.scalars().unique().all())
        except Exception as e:
            log_error(f"Error fetching trending WikiClips for user {user_id}: {e}")
            return []

    async def count_trending(self, user_id: int) -> int:
        """Count total trending WikiClips for a specific user."""
        try:
            query = select(func.count(WikiClip.id)).where(WikiClip.user_id == user_id)
            result = await with_query_timeout(
                self.session.execute(query)
            )
            return result.scalar_one()
        except Exception as e:
            log_error(f"Error counting trending WikiClips for user {user_id}: {e}")
            return 0
