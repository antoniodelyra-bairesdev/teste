from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.db import get_db_manager, DBManager


async def get_session(db_manager: DBManager = Depends(get_db_manager)) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for repositories."""
    async with db_manager.transaction() as session:
        yield session