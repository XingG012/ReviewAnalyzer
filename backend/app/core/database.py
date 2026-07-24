"""
数据库引擎与会话管理 — 基于 SQLAlchemy 2.0 async 模式

提供两个引擎:
  engine       — AsyncEngine (FastAPI 使用)
  sync_engine  — Engine (Celery Worker 使用)
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# 异步引擎 — FastAPI 依赖注入使用
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# 同步引擎 — Celery Worker 使用（Celery 任务不能 await）
sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
sync_engine = create_engine(sync_url, pool_pre_ping=True)

# 异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI 依赖注入：每个请求创建一个异步数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
