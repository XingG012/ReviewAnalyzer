"""pytest 全局 fixtures"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """同步 HTTP 测试客户端"""
    return TestClient(app)
