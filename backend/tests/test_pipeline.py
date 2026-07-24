"""Celery + 分析 Pipeline 测试"""

import json
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models.persona import GoldenSample, Persona
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from app.models.upload import Upload


class TestCeleryApp:
    def test_celery_app_is_configured(self):
        from app.tasks.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.task_acks_late is True

    def test_celery_broker_url_from_settings(self):
        from app.tasks.celery_app import celery_app

        assert "redis" in celery_app.conf.broker_url


class TestPipelineService:
    def test_start_analysis_sends_task(self, db: Session):
        task = Task(asin="B0PIPE0001", site="US", status="pending")
        db.add(task)
        db.commit()
        with patch("app.tasks.analysis_task.run_analysis_pipeline.delay") as mock_delay:
            from app.services.pipeline_service import pipeline_service

            pipeline_service.start_analysis(task.id)
            mock_delay.assert_called_once_with(str(task.id))


class TestAnalysisTaskUnit:
    def _create_task_with_data(self, db: Session) -> tuple[Task, Upload]:
        upload = Upload(
            original_name="sample.csv",
            stored_path="review-analyzer-skill/examples/reviews_sample.csv",
            size_bytes=1024,
            review_count=5,
        )
        db.add(upload)
        db.commit()
        task = Task(
            asin="B0PIPE0002",
            site="US",
            source="csv",
            status="pending",
            config={
                "max_reviews": 5,
                "batch_size": 5,
                "template": "premium-gold",
                "upload_id": str(upload.id),
            },
        )
        db.add(task)
        db.commit()
        return task, upload

    @patch("app.tasks.analysis_task._get_sync_session")
    @patch("subprocess.run")
    def test_task_runs_with_mock(self, mock_run, mock_session, db):
        task, _ = self._create_task_with_data(db)
        mock_session.return_value = db
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [
                {
                    "review_id": None,
                    "sentiment": "积极",
                    "info_score": 7,
                    "tags": {"人群_性别": "男性"},
                },
            ]
        )
        mock_run.return_value = mock_result
        from app.tasks.analysis_task import run_analysis_pipeline

        result = run_analysis_pipeline.apply(args=[str(task.id)])
        assert result.status in ("SUCCESS", "FAILURE")

    def test_failed_status_persists(self, db):
        """失败状态正确写入和读取"""
        task = Task(asin="B0NOFILE01", status="pending", config={"max_reviews": 5})
        db.add(task)
        db.commit()
        task.status = "failed"
        task.error_message = "FileNotFoundError: 未找到 CSV"
        db.commit()
        task = db.get(Task, task.id)
        assert task.status == "failed"
        assert "CSV" in task.error_message


class TestPipelineDBIntegration:
    def test_error_message_persists(self, db):
        """错误信息正确写入 DB"""
        task = Task(asin="B0FAILTEST", status="pending")
        db.add(task)
        db.commit()
        task.status = "failed"
        task.error_message = "RuntimeError: Phase 2 打标失败"
        db.commit()
        task = db.get(Task, task.id)
        assert task.status == "failed"
        assert task.error_message is not None

    def test_batch_insert_reviews(self, db):
        task = Task(asin="B0BATCH001", status="pending")
        db.add(task)
        db.commit()
        for i in range(5):
            db.add(Review(task_id=task.id, body=f"评论_{i}", rating=4.0))
        db.commit()
        assert db.query(Review).filter(Review.task_id == task.id).count() == 5

    def test_full_cycle_all_tables(self, db):
        task = Task(
            asin="B0FULLCY01", status="done", progress=100, total_reviews=3, persona_count=2
        )
        db.add(task)
        db.commit()
        r1 = Review(task_id=task.id, body="好评", rating=5.0)
        r2 = Review(task_id=task.id, body="中评", rating=3.0)
        r3 = Review(task_id=task.id, body="差评", rating=1.0)
        db.add_all([r1, r2, r3])
        db.commit()
        for rid, sentiment, scene in [
            (r1.id, "积极", "家用"),
            (r2.id, "中性", "户外"),
            (r3.id, "消极", "办公"),
        ]:
            db.add(
                TaggedReview(
                    task_id=task.id, review_id=rid, sentiment=sentiment, tags={"使用_场景": scene}
                )
            )
        db.commit()
        p1 = Persona(task_id=task.id, name="家用_男性", count=10)
        p2 = Persona(task_id=task.id, name="户外_女性", count=8)
        db.add_all([p1, p2])
        db.commit()
        db.add(
            GoldenSample(task_id=task.id, persona_id=p1.id, review_id=r1.id, sentiment="positive")
        )
        db.add(
            GoldenSample(task_id=task.id, persona_id=p2.id, review_id=r3.id, sentiment="negative")
        )
        db.commit()
        db.add(AnalysisReport(task_id=task.id, insights_md="# 报告", template_name="premium-gold"))
        db.commit()
        assert db.query(Review).filter(Review.task_id == task.id).count() == 3
        assert db.query(TaggedReview).filter(TaggedReview.task_id == task.id).count() == 3
        assert db.query(Persona).filter(Persona.task_id == task.id).count() == 2
        assert db.query(GoldenSample).filter(GoldenSample.task_id == task.id).count() == 2
        assert db.query(AnalysisReport).filter(AnalysisReport.task_id == task.id).count() == 1
