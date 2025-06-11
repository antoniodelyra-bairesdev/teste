from typing import Optional

from sqlalchemy import select

from ehp.core.models.db.authentication import Authentication
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_error


class AuthenticationRepository(BaseRepository[Authentication]):
    """Authentication repository with specific methods."""

    async def get_by_email(self, email: str) -> Optional[Authentication]:
        if not email:
            return None
        try:
            query = select(self.model).where(self.model.user_email == email)
            return await self.session.scalar(query)
        except Exception as e:
            log_error(f"Error getting auth by email {email}: {e}")
            return None

    async def get_by_username(self, username: str) -> Optional[Authentication]:
        if not username:
            return None
        try:
            query = select(self.model).where(self.model.user_name == username)
            return await self.session.scalar(query)
        except Exception as e:
            log_error(f"Error getting auth by username {username}: {e}")
            return None
