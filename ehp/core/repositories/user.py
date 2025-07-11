import traceback
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ehp.core.models.db.user import User
from ehp.core.models.db.news_category import NewsCategory
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_error


class UserNotFoundException(Exception):
    """Exception raised when a user is not found."""
    pass


class InvalidNewsCategoryException(Exception):
    """Exception raised when invalid news category IDs are provided."""
    pass


class UserRepository(BaseRepository[User]):
    """User repository with specific methods."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_display_name(self, display_name: str) -> Optional[User]:
        """Get user by display name."""
        if not display_name:
            return None
        try:
            query = select(self.model).where(self.model.display_name == display_name)
            return await self.session.scalar(query)
        except Exception as e:
            log_error(f"Error getting user by display_name {display_name}: {e}")
            return None

    async def display_name_exists(
        self, display_name: str, exclude_user_id: Optional[int] = None
    ) -> bool:
        """Check if display name already exists, optionally excluding a specific user."""
        if not display_name:
            return False
        try:
            query = select(self.model).where(self.model.display_name == display_name)
            if exclude_user_id:
                query = query.where(self.model.id != exclude_user_id)
            result = await self.session.scalar(query)
            return result is not None
        except Exception as e:
            log_error(f"Error checking if display_name exists {display_name}: {e}")
            return False
    
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

    async def update_avatar(self, user_id: int, avatar_url: str) -> User:
        """Update user's avatar URL."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(f"User with id {user_id} not found")
            
            user.avatar = avatar_url
            await self.session.commit()
            return user
        except UserNotFoundException:
            raise
        except Exception as e:
            await self.session.rollback()
            log_error(f"Error updating avatar for user {user_id}: {e}\nTraceback: {traceback.format_exc()}")
            raise

    async def update_preferred_news_categories(self, user_id: int, category_ids: List[int]) -> User:
        """Update user's preferred news categories."""
        try:
            # First, validate that all category IDs exist
            if category_ids:
                query = select(NewsCategory.id).where(NewsCategory.id.in_(category_ids))
                result = await self.session.execute(query)
                existing_ids = [row[0] for row in result.fetchall()]
                
                invalid_ids = [cat_id for cat_id in category_ids if cat_id not in existing_ids]
                if invalid_ids:
                    raise InvalidNewsCategoryException(f"Invalid news category IDs: {invalid_ids}")
            
            # Get user
            user = await self.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(f"User with id {user_id} not found")
            
            # Update preferred news categories
            user.preferred_news_categories = category_ids if category_ids else None
            await self.session.commit()
            return user
        except (UserNotFoundException, InvalidNewsCategoryException):
            raise
        except Exception as e:
            await self.session.rollback()
            log_error(f"Error updating preferred news categories for user {user_id}: {e}\nTraceback: {traceback.format_exc()}")
            raise
