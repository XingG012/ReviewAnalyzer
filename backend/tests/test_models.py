"""SQLAlchemy 模型单元测试"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.persona import GoldenSample, Persona
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from app.models.upload import Upload


def test_create_task(db: Session):
    """创建任务，所有字段正确写入"""
    task = Task(
        asin="B0DGV4T6BK",
        site="US",
        source="csv",
        status="pending",
        config={"max_reviews": 100, "template": "premium-gold"},
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    assert task.id is not None
    assert task.asin == "B0DGV4T6BK"
    assert task.site == "US"
    assert task.status == "pending"
    assert task.progress == 0
    assert task.config["max_reviews"] == 100
    assert task.created_at is not None


def test_task_defaults(db: Session):
    """任务默认值正确"""
    task = Task(asin="B000000000")
    db.add(task)
    db.commit()

    assert task.site == "US"
    assert task.source == "csv"
    assert task.status == "pending"
    assert task.progress == 0
    assert task.config == {}
    assert task.total_reviews == 0
    assert task.persona_count == 0


def test_task_check_constraint_status(db: Session):
    """非法 status 触发 CHECK 约束错误"""
    task = Task(asin="B000000000", status="invalid")
    db.add(task)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_task_check_constraint_source(db: Session):
    """非法 source 触发 CHECK 约束错误"""
    task = Task(asin="B000000000", source="invalid")
    db.add(task)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_task_check_constraint_site(db: Session):
    """非法 site 触发 CHECK 约束错误"""
    task = Task(asin="B000000000", site="CN")
    db.add(task)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_task_check_constraint_progress(db: Session):
    """progress > 100 触发 CHECK 约束错误"""
    task = Task(asin="B000000000", progress=150)
    db.add(task)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_cascade_delete_task_deletes_reviews(db: Session):
    """删除 Task 时级联删除关联的 Review 和 TaggedReview"""
    task = Task(asin="B0TEST0001")
    db.add(task)
    db.commit()

    review = Review(task_id=task.id, body="test review", rating=4.5)
    db.add(review)
    db.commit()

    tagged = TaggedReview(
        task_id=task.id, review_id=review.id, sentiment="积极", tags={"人群_性别": "男性"}
    )
    db.add(tagged)
    db.commit()

    db.delete(task)
    db.commit()

    assert db.get(Review, review.id) is None
    assert db.get(TaggedReview, tagged.id) is None


def test_review_unique_constraint(db: Session):
    """同一 task 下 review_id 唯一"""
    task = Task(asin="B0TEST0002")
    db.add(task)
    db.commit()

    r1 = Review(task_id=task.id, body="first", rating=3.0, review_id="R001")
    db.add(r1)
    db.commit()

    r2 = Review(task_id=task.id, body="second", rating=4.0, review_id="R001")
    db.add(r2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_tagged_review_jsonb_tags(db: Session):
    """JSONB tags 字段正确读写 22 维标签"""
    task = Task(asin="B0TEST0003")
    db.add(task)
    db.commit()

    review = Review(task_id=task.id, body="test body", rating=5.0)
    db.add(review)
    db.commit()

    tags = {
        "人群_性别": "女性",
        "人群_年龄段": "25-35岁",
        "使用_场景": "家用",
        "产品_质量": "满意",
    }
    tagged = TaggedReview(
        task_id=task.id, review_id=review.id, sentiment="积极", info_score=8, tags=tags
    )
    db.add(tagged)
    db.commit()
    db.refresh(tagged)

    assert tagged.tags["人群_性别"] == "女性"
    assert tagged.tags["使用_场景"] == "家用"
    assert tagged.info_score == 8


def test_analysis_report_unique_task(db: Session):
    """一个 task 只能有一份报告（unique 约束）"""
    task = Task(asin="B0TEST0004")
    db.add(task)
    db.commit()

    r1 = AnalysisReport(task_id=task.id, insights_md="# Report 1", template_name="premium-gold")
    db.add(r1)
    db.commit()

    r2 = AnalysisReport(task_id=task.id, insights_md="# Report 2", template_name="dark-tech")
    db.add(r2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_persona_with_golden_samples(db: Session):
    """Persona 关联 GoldenSample 正确"""
    task = Task(asin="B0TEST0005")
    db.add(task)
    db.commit()

    review = Review(task_id=task.id, body="sample review", rating=4.0)
    db.add(review)
    db.commit()

    persona = Persona(
        task_id=task.id,
        name="家用_女性",
        count=10,
        dimension="场景_性别",
        tags={"场景": "家用", "性别": "女性"},
    )
    db.add(persona)
    db.commit()

    sample = GoldenSample(
        task_id=task.id,
        persona_id=persona.id,
        review_id=review.id,
        sentiment="positive",
    )
    db.add(sample)
    db.commit()
    db.refresh(persona)

    assert len(persona.golden_samples) == 1
    assert persona.golden_samples[0].sentiment == "positive"


def test_upload_model(db: Session):
    """Upload 模型基本 CRUD"""
    upload = Upload(
        original_name="test_reviews.csv",
        stored_path="minio://bucket/test_reviews.csv",
        size_bytes=1024000,
        review_count=480,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    assert upload.original_name == "test_reviews.csv"
    assert upload.review_count == 480
    assert upload.storage_backend == "minio"
