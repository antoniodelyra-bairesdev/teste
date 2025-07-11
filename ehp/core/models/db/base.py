from datetime import date, datetime
from decimal import Decimal
from functools import cached_property, lru_cache
from typing import Any, Dict, Set
import uuid

from ehp.db import Base

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
    """Updated BaseModel - only serialization, no direct DB access"""

    __abstract__ = True

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

    @classmethod
    @lru_cache
    def _get_mapper_columns(cls) -> Set[str]:
        if not hasattr(cls, "__mapper__"):
            return set()
        return {attr for attr in cls.__mapper__.c.keys()}

    async def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        if not hasattr(self, "__mapper__"):
            return {}

        columns = self._get_mapper_columns()
        return {attr: _serialize_value(getattr(self, attr)) for attr in columns}
