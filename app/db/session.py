from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session


async def init_db() -> None:
    if settings.database_url.startswith("sqlite+aiosqlite:///"):
        sync_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite", 1)
        sync_engine = create_engine(sync_url, future=True)
        Base.metadata.create_all(sync_engine)
        sync_engine.dispose()
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
