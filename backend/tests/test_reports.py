"""Step 7 — 报告查询 + 评论数据 HTTP 集成测试

每个测试都走完整的 HTTP 请求/响应管道，验证状态码、响应体、数据结构。
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.persona import GoldenSample, Persona
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from tests.conftest import make_data_visible


def _setup_task(db: Session, asin: str = "B0RPT00001", **kwargs) -> Task:
    defaults = {"status": "done", "progress": 100, "total_reviews": 3, "persona_count": 2}
    defaults.update(kwargs)
    task = Task(asin=asin, site="US", source="csv", **defaults)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _setup_reviews(db: Session, task_id) -> list[Review]:
    reviews = [
        Review(task_id=task_id, body="好评内容AAA", rating=5.0, author="用户A"),
        Review(task_id=task_id, body="中评内容BBB", rating=3.0, author="用户B"),
        Review(task_id=task_id, body="差评内容CCC", rating=1.0, author="用户C"),
    ]
    db.add_all(reviews)
    db.commit()
    for r in reviews:
        db.refresh(r)
    return reviews


def _setup_tagged(db: Session, task_id, reviews: list[Review]) -> None:
    tagged = [
        TaggedReview(task_id=task_id, review_id=reviews[0].id,
                     sentiment="积极", info_score=8,
                     tags={"人群_性别": "女性", "使用_场景": "家用"}),
        TaggedReview(task_id=task_id, review_id=reviews[1].id,
                     sentiment="中性", info_score=5,
                     tags={"人群_性别": "男性", "使用_场景": "户外"}),
        TaggedReview(task_id=task_id, review_id=reviews[2].id,
                     sentiment="消极", info_score=2,
                     tags={"人群_性别": "女性", "使用_场景": "办公"}),
    ]
    db.add_all(tagged)
    db.commit()


def _setup_report(db: Session, task_id) -> None:
    report = AnalysisReport(
        task_id=task_id,
        insights_md="# 洞察报告\n\n## 第一章\n\n测试报告内容。",
        stats={"total_reviews": 3, "avg_rating": 3.0},
        chart_configs={"sentiment_pie": {"labels": ["积极", "中性", "消极"]}},
        html_content="<html><body><h1>测试看板</h1></body></html>",
        template_name="premium-gold",
    )
    db.add(report)
    db.commit()


def _setup_personas(db: Session, task_id, reviews: list[Review]) -> None:
    p1 = Persona(task_id=task_id, name="家用_女性", count=10,
                 tags={"场景": "家用", "性别": "女性"}, color="#ec4899",
                 summary="以家庭使用场景为主的女性用户")
    p2 = Persona(task_id=task_id, name="户外_男性", count=8,
                 tags={"场景": "户外", "性别": "男性"}, color="#3b82f6",
                 summary="户外活动爱好者群体")
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)
    db.add(GoldenSample(task_id=task_id, persona_id=p1.id, review_id=reviews[0].id,
                        sentiment="positive"))
    db.add(GoldenSample(task_id=task_id, persona_id=p2.id, review_id=reviews[1].id,
                        sentiment="negative"))
    db.commit()


def _setup_complete(db: Session, asin: str = "B0RPT00001") -> Task:
    """创建完整测试数据：task + reviews + tagged + report + personas"""
    task = _setup_task(db, asin=asin)
    reviews = _setup_reviews(db, task.id)
    _setup_tagged(db, task.id, reviews)
    _setup_report(db, task.id)
    _setup_personas(db, task.id, reviews)
    return task


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/report
# ═══════════════════════════════════════════════════════════════

class TestReportEndpoint:
    """HTTP 层: 报告查询端点"""

    def test_report_200_with_full_body(self, db: Session, client: TestClient):
        """已完成任务返回 200 + 完整 JSON 结构"""
        task = _setup_complete(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/report")
        assert resp.status_code == 200
        body = resp.json()
        assert body["template_name"] == "premium-gold"
        assert "insights_md" in body
        assert len(body["insights_md"]) > 0
        assert "stats" in body
        assert body["stats"]["total_reviews"] == 3
        assert "chart_configs" in body

    def test_report_pending_task_404(self, db: Session, client: TestClient):
        """pending 任务返回 404 + 状态提示"""
        task = _setup_task(db, status="pending", progress=0)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/report")
        assert resp.status_code == 404
        assert "pending" in resp.json()["detail"]

    def test_report_failed_task_404(self, db: Session, client: TestClient):
        """failed 任务返回 404"""
        task = _setup_task(db, status="failed", error_message="timeout")
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/report")
        assert resp.status_code == 404
        assert "失败" in resp.json()["detail"]

    def test_report_nonexistent_404(self, client: TestClient):
        """不存在的任务返回 404"""
        resp = client.get(f"/api/tasks/{uuid4()}/report")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/reviews
# ═══════════════════════════════════════════════════════════════

class TestReviewsEndpoint:
    """HTTP 层: 评论查询端点"""

    def test_reviews_200_paginated(self, db: Session, client: TestClient):
        task = _setup_complete(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/reviews?offset=0&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["reviews"]) == 2
        assert body["reviews"][0]["body"] is not None

    def test_reviews_rating_filter(self, db: Session, client: TestClient):
        task = _setup_complete(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/reviews?rating_min=4&rating_max=5")
        assert resp.status_code == 200
        body = resp.json()
        assert all(r["rating"] >= 4 for r in body["reviews"])


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/tagged
# ═══════════════════════════════════════════════════════════════

class TestTaggedEndpoint:
    """HTTP 层: 打标结果查询端点"""

    def test_tagged_200_with_review_body(self, db: Session, client: TestClient):
        task = _setup_complete(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/tagged?offset=0&limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        # 每条打标结果应包含原始评论正文
        for tr in body["tagged_reviews"]:
            assert tr["review_body"] is not None
            assert tr["sentiment"] is not None

    def test_tagged_filter_by_tag(self, db: Session, client: TestClient):
        """标签筛选：人群_性别=女性"""
        task = _setup_complete(db)
        make_data_visible(db)

        # URL 编码中文参数
        resp = client.get(
            f"/api/tasks/{task.id}/tagged",
            params={"tag_key": "人群_性别", "tag_value": "女性"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2  # review[0] 和 review[2]
        for tr in body["tagged_reviews"]:
            assert tr["tags"]["人群_性别"] == "女性"


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/personas
# ═══════════════════════════════════════════════════════════════

class TestPersonasEndpoint:
    """HTTP 层: 用户画像查询端点"""

    def test_personas_200_with_samples(self, db: Session, client: TestClient):
        task = _setup_complete(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/personas")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        p1 = body[0]
        assert p1["name"] in ("家用_女性", "户外_男性")
        assert "golden_samples" in p1
        # 黄金样本应包含 review_body
        if p1["golden_samples"]:
            assert p1["golden_samples"][0]["review_body"] is not None

    def test_personas_empty_list(self, db: Session, client: TestClient):
        task = _setup_task(db)
        _setup_report(db, task.id)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/personas")
        assert resp.status_code == 200
        assert resp.json() == []
