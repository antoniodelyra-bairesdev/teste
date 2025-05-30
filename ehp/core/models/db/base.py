from datetime import date, datetime
from decimal import Decimal
from functools import cached_property, lru_cache
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)
import uuid

from sqlalchemy import func, select
from sqlalchemy.sql import exists

from ehp.db import Base, DBManager, get_async_page_info
from ehp.base.middleware import get_current_request
from ehp.utils.base import log_error


ALL_DELETE_ORPHAN = "all, delete-orphan"


def _serialize_value(value: Any) -> Any:
    """Serialize different types of values"""
    if value is None:
        return None
    elif isinstance(value, (date, datetime)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return str(value)
    elif isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class BaseModel(Base):
    __abstract__ = True
    _mapper_attrs: Dict[str, Set[str]] = {}
    _db_manager = None

    @cached_property
    def _class_name(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        try:
            id_value = getattr(self, "id", None)
            return (
                f"<{self._class_name}{f' {id_value}' if id_value is not None else ''}>"
            )
        except Exception as e:
            return f"An error {e} occurred in class: <{self._class_name}>"

    # Define serialization formats
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

    @classmethod
    @lru_cache
    def _get_mapper_columns(cls) -> Set[str]:
        if not hasattr(cls, "__mapper__"):
            return set()
        return {attr for attr in cls.__mapper__.c.keys()}

    async def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary with options for inclusion/exclusion

        """
        if not hasattr(self, "__mapper__"):
            return {}

        # Get cached column names
        columns = self._get_mapper_columns()

        return {attr: _serialize_value(getattr(self, attr)) for attr in columns}

    async def to_dict_flat(self) -> Dict[str, Any]:
        """Simplified version for when you just need basic serialization"""
        if not hasattr(self, "__mapper__"):
            return {}

        return {attr: getattr(self, attr) for attr in self._get_mapper_columns()}

    @cached_property
    def _json_encoders(self) -> Dict[type, callable]:
        """Cache the type encoders"""
        return {
            datetime: lambda x: x.isoformat(),
            uuid.UUID: str,
            # Add other types as needed
        }

    async def serialize(self) -> Dict[str, Any]:
        """Simple alias for to_dict"""
        return await self.to_dict()

    async def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dict"""

        async def extended_encoder(x: Any) -> Any:
            # Get encoder from cached mapping
            encoder = self._json_encoders.get(type(x))
            if encoder:
                return encoder(x)
            return x

        # Avoid double conversion by using the encoder directly
        return {k: extended_encoder(v) for k, v in (await self.to_dict()).items()}

    @classmethod
    async def get_db_manager(cls) -> DBManager:
        request = get_current_request()
        return request.state.request_config.get("db_manager")

    # moved to the repository
    @classmethod
    async def exists(cls, obj_id: int) -> bool:
        if not obj_id or not hasattr(cls, "id"):
            return False

        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                stmt = select(exists().where(cls.id == obj_id))
                result = await session.scalar(stmt)
                return bool(result)
        except Exception as e:
            log_error(f"Error checking existence of {cls.__name__} id {obj_id}: {e}")
            return False

    # moved to the repository
    @classmethod
    async def get_by_id(cls, obj_id: int) -> Optional[Any]:
        if not obj_id:
            return None

        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                return await session.get(cls, obj_id)
        except Exception as e:
            log_error(f"Error getting {cls.__name__} by id {obj_id}: {e}")
            return None

    # moved to the repository
    @classmethod
    async def list(cls) -> List[Any]:
        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                stmt = select(cls).execution_options(populate_existing=True)
                result = await session.scalars(stmt)
                return list(result)
        except Exception as e:
            log_error(f"Error listing {cls.__name__}: {e}")
            return []

    # Cache the status check at class level
    _has_status: ClassVar[bool] = None
    _has_active: ClassVar[bool] = None

    @classmethod
    async def _get_active_condition(cls) -> Optional[bool]:
        """Cache the column check at class level to avoid repeated hasattr calls"""
        if cls._has_status is None:
            cls._has_status = hasattr(cls, "status")
        if cls._has_active is None:
            cls._has_active = hasattr(cls, "active")

        if cls._has_status:
            return cls.status == "1"
        elif cls._has_active:
            return cls.active == "1"
        return None

    @classmethod
    async def get_active_by_id(cls, obj_id: int) -> Optional[Any]:
        if not obj_id:
            return None

        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                # Get the active condition (now cached)
                active_condition = await cls._get_active_condition()

                if active_condition is not None:
                    # Both conditions in one query
                    return await session.get(
                        cls,
                        obj_id,
                        with_for_update={"read": True},  # Add if you need row locking
                    )
                else:
                    # Just get by ID if no active condition
                    return await session.get(cls, obj_id)
        except Exception as e:
            log_error(e)
            return None

    # moved to the repository
    @classmethod
    async def list_paged(cls, page: int) -> Tuple[List[Any], int, int]:
        try:
            return await get_async_page_info(
                select(cls), page, db_manager=await cls.get_db_manager()
            )
        except Exception as e:
            log_error(e)
        return [], 0, 0

    @classmethod
    async def obj_delete(cls, obj_id: int) -> bool:
        if not obj_id:
            return False

        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                # Get the object directly
                obj = await session.get(cls, obj_id)
                if not obj:
                    return False

                # Delete the object
                await session.delete(obj)
                await session.flush()
                return True

        except Exception as e:
            log_error(f"Error deleting {cls.__name__} with id {obj_id}: {str(e)}")
            return False

    @classmethod
    async def count_by_id(cls) -> int:
        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                stmt = (
                    select(func.count())
                    .select_from(select(cls.id).subquery())
                    .execution_options(populate_existing=True)
                )

                # Use scalar() directly
                result = await session.scalar(stmt)
            return int(result or 0)  # Handle None case
        except Exception as e:
            log_error(e)
        return 0

    @classmethod
    async def count_by_id_and_status(cls, status: str) -> int:
        if not status:  # Early return for invalid status
            return 0

        try:
            db_manager = await cls.get_db_manager()
            async with db_manager.transaction() as session:
                # Optimize count query with subquery
                stmt = (
                    select(func.count())
                    .select_from(select(cls.id).where(cls.status == status).subquery())
                    .execution_options(populate_existing=True)
                )

                result = await session.scalar(stmt)
                return int(result or 0)  # Handle None case

        except Exception as e:
            log_error(e)
            return 0

    @classmethod
    async def list_by_status_paged(
        cls, status: str, page: int
    ) -> Tuple[List[Any], int, int]:
        if not status:  # Early return
            return [], 0, 0

        try:
            # Build optimized base query
            base_query = (
                select(cls)
                .where(cls.status == status)
                .order_by(cls.id)  # Add consistent ordering
                .execution_options(populate_existing=True)
            )
            return await get_async_page_info(
                query=base_query,
                page=page,
                db_manager=await cls.get_db_manager(),
            )
        except Exception as e:
            log_error(e)
        return [], 0, 0

    @classmethod
    async def list_all_online_paged(cls, page: int) -> Tuple[List[Any], int, int]:
        try:
            # Build optimized base query
            base_query = (
                select(cls)
                .where(cls.is_online == "1")
                .order_by(cls.id)  # Add consistent ordering
                .execution_options(
                    populate_existing=True,
                )
            )

            return await get_async_page_info(
                query=base_query, page=page, db_manager=await cls.get_db_manager()
            )
        except Exception as e:
            log_error(e)
        return [], 0, 0

    @classmethod
    async def get_by_code(cls, code: str) -> Any:
        if code:
            try:
                db_manager = await cls.get_db_manager()
                async with db_manager.transaction() as session:
                    query = select(cls).where(cls.code == code)
                    return await session.scalar(query)
            except Exception as e:
                log_error(e)
        return None
