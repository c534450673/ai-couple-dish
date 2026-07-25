from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = structlog.get_logger()


class Database:
    """管理异步 SQLAlchemy 引擎与请求级会话。"""

    def __init__(self, url: str, *, pool_size: int, max_overflow: int) -> None:
        self.engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self._factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def connect(self) -> None:
        await self.ping()

    async def close(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> bool:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                await logger.awarning(
                    "database_session_rolled_back",
                    module="database",
                    operation="rollback",
                    result="completed",
                    dependency="database",
                )
                raise


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """为每次 FastAPI 依赖调用提供独立会话。"""
    async with request.app.state.db.session() as session:
        yield session
