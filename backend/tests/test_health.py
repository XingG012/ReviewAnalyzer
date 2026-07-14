"""健康检查端点测试"""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    """GET /api/health 返回状态 ok 和版本号"""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


def test_health_response_is_json(client: TestClient):
    """健康检查返回 JSON Content-Type"""
    response = client.get("/api/health")

    assert "application/json" in response.headers["content-type"]
