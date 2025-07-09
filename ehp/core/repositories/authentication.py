from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.authentication import Authentication
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_error


class AuthNotFoundException(Exception):
    """Exception raised when an authentication record is not found."""
    pass


class AuthenticationRepository(BaseRepository[Authentication]):
    """Authentication repository with specific methods."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Authentication)

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
    
    async def update_password(self, auth_id: int, new_password_hash: str) -> bool:
        """Update user's password."""
        try:
            auth = await self.get_by_id(auth_id)
            if auth:
                auth.user_pwd = new_password_hash
                await self.session.commit()
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            log_error(f"Error updating password for auth_id {auth_id}: {e}")
            return False
