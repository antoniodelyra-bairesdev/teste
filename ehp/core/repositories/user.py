import traceback
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ehp.core.models.db.user import User
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_error


class UserNotFoundException(Exception):
    """Exception raised when a user is not found."""
    pass


class UserRepository(BaseRepository[User]):
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_auth_id(self, auth_id: int) -> Optional[User]:
        """Get user by authentication ID."""
        try:
            query = select(User).where(User.auth_id == auth_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            log_error(f"Error getting user by auth_id {auth_id}: {e}\nTraceback: {traceback.format_exc()}")
            return None
    
    async def update_full_name(self, user_id: int, full_name: str) -> User:
        """Update user's full name."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(f"User with id {user_id} not found")
            
            user.full_name = full_name
            # CRITICAL: Need to commit changes to the DB
            await self.session.commit()
            return user
        except UserNotFoundException:
            raise
        except Exception as e:
            await self.session.rollback()  # Crucial if commit() fails
            log_error(f"Error updating full_name for user {user_id}: {e}\nTraceback: {traceback.format_exc()}")
            raise
