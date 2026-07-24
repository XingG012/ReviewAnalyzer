"""Step 7 — 文件导出 HTTP 集成测试

每个测试走完整的 HTTP 请求/响应管道，验证状态码、Content-Type、Content-Disposition、响应体内容。
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from tests.conftest import make_data_visible


def _setup_export_data(db: Session) -> Task:
    """创建完整的 done 任务 + tagged reviews + report"""
    task = Task(asin="B0EXPORT01", site="US", source="csv",
                status="done", progress=100, total_reviews=2, persona_count=1)
    db.add(task)
    db.commit()
    db.refresh(task)

    r1 = Review(task_id=task.id, body="好评内容AAA", rating=5.0, author="用户A")
    r2 = Review(task_id=task.id, body="差评内容BBB", rating=1.0, author="用户B")
    db.add_all([r1, r2])
    db.commit()
    db.refresh(r1)
    db.refresh(r2)

    db.add(TaggedReview(task_id=task.id, review_id=r1.id,
                        sentiment="积极", info_score=8,
                        tags={"人群_性别": "女性", "使用_场景": "家用", "产品_质量": "满意"}))
    db.add(TaggedReview(task_id=task.id, review_id=r2.id,
                        sentiment="消极", info_score=3,
                        tags={"人群_性别": "男性", "产品_性价比": "低"}))
    db.commit()

    db.add(AnalysisReport(
        task_id=task.id,
        insights_md="# 测试洞察报告\n\n## 第一章\n\n报告正文。",
        html_content="<html><body><h1>测试看板</h1></body></html>",
        template_name="premium-gold",
        stats={"total_reviews": 2},
    ))
    db.commit()
    return task


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/export/csv
# ═══════════════════════════════════════════════════════════════

class TestExportCSV:
    """HTTP 层: CSV 导出端点"""

    def test_csv_200_content_type(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "utf-8" in resp.headers["content-type"]

    def test_csv_200_filename_header(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/csv")
        assert resp.status_code == 200
        disposition = resp.headers["content-disposition"]
        assert task.asin in disposition
        assert ".csv" in disposition
        # 文件名必须是 ASCII（HTTP header latin-1 限制）
        assert "attachment" in disposition

    def test_csv_200_utf8_bom_and_columns(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/csv")
        assert resp.status_code == 200
        text = resp.text
        # UTF-8 BOM
        assert text.startswith("﻿")
        # 包含固定列 + 动态标签列
        assert "review_id" in text
        assert "sentiment" in text
        assert "info_score" in text
        assert "人群_性别" in text
        # 数据行
        assert "好评内容AAA" in text

    def test_csv_pending_task_404(self, db: Session, client: TestClient):
        task = Task(asin="B0PENDING1", status="pending", progress=0)
        db.add(task)
        db.commit()
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/csv")
        assert resp.status_code == 404

    def test_csv_nonexistent_404(self, client: TestClient):
        resp = client.get(f"/api/tasks/{uuid4()}/export/csv")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/export/md
# ═══════════════════════════════════════════════════════════════

class TestExportMD:
    """HTTP 层: Markdown 导出端点"""

    def test_md_200_content_type(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/md")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]

    def test_md_200_contains_report(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/md")
        assert resp.status_code == 200
        assert "# 测试洞察报告" in resp.text
        assert "## 第一章" in resp.text

    def test_md_200_filename_ascii(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/md")
        assert resp.status_code == 200
        disposition = resp.headers["content-disposition"]
        assert task.asin in disposition
        assert ".md" in disposition

    def test_md_no_report_404(self, db: Session, client: TestClient):
        task = Task(asin="B0NOMD0001", status="done", progress=100)
        db.add(task)
        db.commit()
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/md")
        assert resp.status_code == 404

    def test_md_pending_task_404(self, db: Session, client: TestClient):
        task = Task(asin="B0NOMD0002", status="pending", progress=0)
        db.add(task)
        db.commit()
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/md")
        assert resp.status_code == 404

    def test_md_nonexistent_404(self, client: TestClient):
        resp = client.get(f"/api/tasks/{uuid4()}/export/md")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# GET /{task_id}/export/html
# ═══════════════════════════════════════════════════════════════

class TestExportHTML:
    """HTTP 层: HTML 导出端点"""

    def test_html_200_content_type(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_html_200_contains_board(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/html")
        assert resp.status_code == 200
        assert "<html>" in resp.text
        assert "测试看板" in resp.text

    def test_html_200_filename_ascii(self, db: Session, client: TestClient):
        task = _setup_export_data(db)
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/html")
        assert resp.status_code == 200
        disposition = resp.headers["content-disposition"]
        assert task.asin in disposition
        assert ".html" in disposition

    def test_html_no_content_404(self, db: Session, client: TestClient):
        task = Task(asin="B0NOHTML01", status="done", progress=100)
        db.add(task)
        db.commit()
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/html")
        assert resp.status_code == 404

    def test_html_pending_task_404(self, db: Session, client: TestClient):
        task = Task(asin="B0NOHTML02", status="pending", progress=0)
        db.add(task)
        db.commit()
        make_data_visible(db)

        resp = client.get(f"/api/tasks/{task.id}/export/html")
        assert resp.status_code == 404

    def test_html_nonexistent_404(self, client: TestClient):
        resp = client.get(f"/api/tasks/{uuid4()}/export/html")
        assert resp.status_code == 404
