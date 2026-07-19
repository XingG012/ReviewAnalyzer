"""pytest 全局 fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.main import app

# 测试用同步数据库连接（复用同一个 PG 实例）
sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
test_engine = create_engine(sync_url)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Session:
    """同步数据库会话，每个测试独立事务，测试后自动回滚"""
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
