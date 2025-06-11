from contextlib import asynccontextmanager
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
import ssl

from ehp.config import settings


ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

engine = create_async_engine(
    settings.SQLALCHEMY_ASYNC_DATABASE_URI,
    pool_size=100,
    max_overflow=50,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"ssl": ssl_context},
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


Base = declarative_base()


async def get_db_session() -> AsyncSession:
    return async_session_factory()


@asynccontextmanager
async def get_db_session_context():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_metadata() -> MetaData:
    metadata = MetaData()
    async with engine.begin() as conn:
        metadata.reflect(bind=conn)
    return metadata


async def close_db_session(session: AsyncSession) -> None:
    if session:
        await session.close()
