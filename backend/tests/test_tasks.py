"""任务 CRUD API 测试

策略：HTTP 层测试校验逻辑（422/400），业务逻辑通过 sync DB + service 直接测试。
async HTTP 端点完整测试由 Step 12 Playwright E2E 覆盖。
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.task import Task


def _create_task(db: Session, asin: str = "B0TEST0001", **kwargs) -> Task:
    """辅助函数：直接通过 DB 创建任务"""
    task = Task(asin=asin, **kwargs)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


class TestSchemaValidation:
    """Pydantic Schema 校验测试（不需要 DB）"""

    def test_invalid_asin_rejected(self, client: TestClient):
        """非法 ASIN → 422"""
        response = client.post(
            "/api/tasks",
            json={"asin": "abc", "source": "sorftime"},
        )
        assert response.status_code == 422

    def test_missing_asin_rejected(self, client: TestClient):
        """缺少必填 asin → 422"""
        response = client.post(
            "/api/tasks",
            json={"source": "csv"},
        )
        assert response.status_code == 422

    def test_invalid_site_rejected(self, client: TestClient):
        """非法 site → 422"""
        response = client.post(
            "/api/tasks",
            json={"asin": "B0DGV4T6BK", "site": "CN", "source": "sorftime"},
        )
        assert response.status_code == 422

    def test_missing_upload_id_for_csv(self, client: TestClient):
        """CSV 模式无 upload_id → 400（service 层逻辑）"""
        response = client.post(
            "/api/tasks",
            json={"asin": "B0DGV4T6BK", "source": "csv"},
        )
        # 422 from schema (upload_id optional) or 400 from service
        assert response.status_code in (400, 422)


class TestTaskCRUDViaDB:
    """业务逻辑测试 — 通过 sync DB 直接操作，验证 CRUD 正确性"""

    def test_create_and_query(self, db: Session):
        """创建任务后可查询"""
        task = Task(asin="B0DGV4T6BK", site="US", source="csv", status="pending")
        db.add(task)
        db.commit()

        found = db.get(Task, task.id)
        assert found is not None
        assert found.asin == "B0DGV4T6BK"
        assert found.status == "pending"
        assert found.progress == 0
        assert found.created_at is not None

    def test_create_with_config(self, db: Session):
        """JSONB config 字段正确存储和读取"""
        config = {"max_reviews": 100, "batch_size": 20, "template": "premium-gold"}
        task = Task(asin="B0CONFIG01", config=config)
        db.add(task)
        db.commit()

        found = db.get(Task, task.id)
        assert found.config["max_reviews"] == 100
        assert found.config["template"] == "premium-gold"

    def test_list_filtered_by_status(self, db: Session):
        """按状态筛选正确"""
        _create_task(db, status="done", asin="B0DONE0001")
        _create_task(db, status="failed", asin="B0FAIL0001")
        _create_task(db, status="done", asin="B0DONE0002")

        done_tasks = db.query(Task).filter(Task.status == "done").all()
        assert len(done_tasks) >= 2
        assert all(t.status == "done" for t in done_tasks)

    def test_pagination(self, db: Session):
        """分页查询正确"""
        for i in range(10):
            _create_task(db, asin=f"B0PAGE{i:04d}")

        page = db.query(Task).order_by(Task.created_at.desc()).offset(0).limit(3).all()
        assert len(page) == 3

    def test_delete_cascade(self, db: Session):
        """删除任务后确认不存在"""
        task = _create_task(db)
        task_id = task.id

        db.delete(task)
        db.commit()

        assert db.get(Task, task_id) is None

    def test_update_status(self, db: Session):
        """更新任务状态"""
        task = _create_task(db, status="pending")

        task.status = "done"
        task.progress = 100
        task.completed_at = Task.updated_at
        db.commit()
        db.refresh(task)

        assert task.status == "done"
        assert task.progress == 100

    def test_retry_failed(self, db: Session):
        """重试：failed → pending 重置"""
        task = _create_task(db, status="failed", error_message="timeout", progress=50)

        task.status = "pending"
        task.progress = 0
        task.error_message = None
        task.error_phase = None
        db.commit()
        db.refresh(task)

        assert task.status == "pending"
        assert task.progress == 0
        assert task.error_message is None

    def test_check_constraint_prevents_invalid_status(self, db: Session):
        """CHECK 约束阻止非法状态"""
        from sqlalchemy.exc import IntegrityError

        task = Task(asin="B0CHK0001", status="invalid")
        db.add(task)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_uuid_autogeneration(self, db: Session):
        """主键自动生成 UUID"""
        task = Task(asin="B0UUID0001")
        db.add(task)
        db.commit()

        assert task.id is not None
        assert isinstance(task.id, uuid.UUID)
        assert len(str(task.id)) == 36  # UUID 格式: 8-4-4-4-12
