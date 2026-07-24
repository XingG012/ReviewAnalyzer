"""pytest 全局 fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.main import app

# 测试用同步数据库连接（复用同一个 PG 实例）
sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
test_engine = create_engine(sync_url)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def _patch_async_engine():
    """用 NullPool 替换 async engine，防止跨 event loop 连接泄漏。

    FastAPI TestClient 每次请求使用独立 event loop，默认连接池
    会在 loop 关闭后残留连接，导致 RuntimeError: different loop。
    NullPool 每次新建连接，用完即弃，无此问题。
    """
    import app.core.database as db_module

    test_async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    db_module.engine = test_async_engine
    db_module.async_session = async_sessionmaker(
        test_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture(scope="function")
def db() -> Session:
    """同步数据库会话，每个测试独立事务，测试后自动回滚。

    纯数据层测试（不涉及 HTTP）使用此 fixture。
    数据在事务内可见，测试后自动撤销无需手动清理。
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSession(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client() -> TestClient:
    """FastAPI 测试客户端"""
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════
# HTTP 集成测试工具
# ═══════════════════════════════════════════════════════════════

def make_data_visible(session: Session) -> None:
    """将当前事务中的数据提交到 PostgreSQL，使 async get_db() 可见。

    调用后数据对 FastAPI 的 async 会话可见，同时开启新事务
    保持 cleanup 隔离性（测试结束后 fixture 回滚新事务）。

    用法：在 db fixture 中创建数据 → 调用 make_data_visible(db) → 发 HTTP 请求
    """
    session.flush()
    # 提交外层事务（connection.begin() 开启的那个）
    session.execute(text("COMMIT"))
    # 立即开启新事务，保证 fixture cleanup 时 rollback 仍有效
    session.execute(text("BEGIN"))
