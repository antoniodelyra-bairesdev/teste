from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.utils.base import log_error

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Repository interface defining common data access operations."""

    @abstractmethod
    async def get_by_id(self, obj_id: int) -> Optional[T]:
        pass

    @abstractmethod
    async def list_all(self) -> List[T]:
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, obj_id: int) -> bool:
        pass


class BaseRepository(Repository[T], Generic[T]):
    """Simple base repository implementation."""

    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, obj_id: int) -> Optional[T]:
        if not obj_id:
            return None
        try:
            return await self.session.get(self.model, obj_id)
        except Exception as e:
            log_error(f"Error getting {self.model.__name__} by id {obj_id}: {e}")
            return None

    async def list_all(self) -> List[T]:
        try:
            result = await self.session.scalars(select(self.model))
            return list(result)
        except Exception as e:
            log_error(f"Error listing {self.model.__name__}: {e}")
            return []

    async def create(self, entity: T) -> T:
        try:
            self.session.add(entity)
            await self.session.flush()
            return entity
        except Exception as e:
            log_error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(self, entity: T) -> T:
        try:
            await self.session.flush()
            return entity
        except Exception as e:
            log_error(f"Error updating {self.model.__name__}: {e}")
            raise

    async def delete(self, obj_id: int) -> bool:
        if not obj_id:
            return False
        try:
            obj = await self.session.get(self.model, obj_id)
            if obj:
                await self.session.delete(obj)
                await self.session.flush()
                return True
            return False
        except Exception as e:
            log_error(f"Error deleting {self.model.__name__} with id {obj_id}: {e}")
            return False
