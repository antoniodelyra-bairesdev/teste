from datetime import date
from typing import Optional

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_debug, log_error


class WikiClipRepository(BaseRepository[WikiClip]):
    """Repository for WikiClip operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, WikiClip)

    async def get_by_url(self, url: str) -> Optional[WikiClip]:
        """Get WikiClip by URL."""
        if not url:
            return None
        try:
            result = await self.session.execute(
                select(WikiClip).where(WikiClip.url == url)
            )
            wikiclip = result.scalar_one_or_none()
            if wikiclip is None:
                log_debug(f"No WikiClip found for URL: {url}")
            return wikiclip
        except Exception as e:
            log_error(f"Error getting WikiClip by url {url}: {e}")
            return None

    async def exists(self, url: str, date: date, title: str, user_id: int) -> bool:
        try:
            statement = select(
                exists().where(
                    and_(
                        WikiClip.url == url,
                        func.date(WikiClip.date) == date,
                        WikiClip.title == title,
                        WikiClip.user_id == user_id,
                    )
                )
            )
        except Exception as e:
            log_error(
                "Error checking if WikiClip exists for URL "
                + f"{url}, date {date}, title {title} and {user_id}: {e}"
            )
            return False
        else:
            result = await self.session.execute(statement)
            exists_result = result.scalar_one()
            if not exists_result:
                log_debug(
                    f"No WikiClip exists for URL: {url}, date: {date}, title: {title}"
                )
            return exists_result
