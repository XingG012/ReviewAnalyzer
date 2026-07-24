"""Celery 分析任务 + SSE 进度推送"""

import sys
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.persona import GoldenSample, Persona
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from app.models.upload import Upload
from app.tasks.celery_app import celery_app

_ENGINE_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "review-analyzer-skill"
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))


def _get_sync_session() -> Session:
    from app.core.database import sync_engine

    return Session(sync_engine)


def _publish_sse(task_id: UUID, event: str, data: dict):
    with suppress(Exception):
        from app.services.sse_manager import sse_manager

        sse_manager.publish(task_id, event, data)


@celery_app.task(bind=True, max_retries=3)
def run_analysis_pipeline(self, task_id: str) -> dict:
    task_uuid = UUID(task_id)
    session = _get_sync_session()

    try:
        task = session.get(Task, task_uuid)
        if task is None:
            raise ValueError(f"任务不存在: {task_id}")

        task.status = "fetching"
        task.started_at = datetime.now(UTC)
        session.commit()

        config = task.config or {}
        max_reviews = config.get("max_reviews", 500)
        batch_size = config.get("batch_size", 20)
        template = config.get("template", "premium-gold")

        # Phase 1
        _update_progress(task, session, 1, "fetching", 10, "正在加载评论数据...")
        csv_path = _get_csv_path(session, config, task_id)
        reviews_data = _load_reviews(csv_path, max_reviews)
        for r in reviews_data:
            session.add(
                Review(
                    task_id=task.id,
                    review_id=r.get("review_id"),
                    title=r.get("title"),
                    body=r.get("body", ""),
                    rating=float(r.get("rating", 0)),
                    author=r.get("author"),
                    date=r.get("date"),
                )
            )
        session.commit()
        task.total_reviews = len(reviews_data)
        _update_progress(task, session, 1, "tagging", 20, f"已加载 {len(reviews_data)} 条评论")

        # Phase 2
        _update_progress(
            task, session, 2, "tagging", 25, f"正在 AI 打标... (0/{len(reviews_data)})"
        )
        from src.review_analyzer import analyze_all

        tagged_reviews = analyze_all(reviews_data, batch_size=batch_size)
        if not tagged_reviews:
            raise RuntimeError("打标结果为空")
        for tr in tagged_reviews:
            review = (
                session.query(Review)
                .filter(Review.task_id == task.id, Review.review_id == tr.get("review_id"))
                .first()
            )
            if review is None:
                continue
            session.add(
                TaggedReview(
                    task_id=task.id,
                    review_id=review.id,
                    sentiment=tr.get("sentiment"),
                    info_score=tr.get("info_score", 0),
                    tags=tr.get("tags", {}),
                )
            )
        session.commit()
        _update_progress(task, session, 2, "analyzing", 40, f"打标完成 ({len(tagged_reviews)} 条)")

        # Phase 3
        _update_progress(task, session, 3, "analyzing", 45, "正在识别用户画像...")
        from src.user_persona_analyzer import analyze_user_personas

        personas_data, golden_samples_data = analyze_user_personas(tagged_reviews)
        for p in personas_data:
            session.add(
                Persona(
                    task_id=task.id,
                    name=p.get("name", ""),
                    count=p.get("count", 0),
                    dimension=p.get("dimension"),
                    tags=p.get("tags", {}),
                    color=p.get("color", "#6366f1"),
                    summary=p.get("summary"),
                )
            )
        session.commit()
        for gs in golden_samples_data:
            with suppress(ValueError, KeyError):
                session.add(
                    GoldenSample(
                        task_id=task.id,
                        persona_id=UUID(gs["persona_id"]) if gs.get("persona_id") else None,
                        review_id=UUID(gs["review_id"]) if gs.get("review_id") else None,
                        sentiment=gs.get("sentiment"),
                        sentiment_class=gs.get("sentiment_class"),
                    )
                )
        session.commit()
        task.persona_count = len(personas_data)
        _update_progress(task, session, 3, "rendering", 60, f"识别到 {len(personas_data)} 个画像")

        # Phase 4
        _update_progress(task, session, 4, "rendering", 65, "正在生成 14 章洞察报告...")
        from src.insights_generator import calculate_stats_summary, generate_insights

        stats = calculate_stats_summary(tagged_reviews)
        insights_md = generate_insights(
            stats=stats,
            personas=personas_data,
            golden_samples=golden_samples_data,
            asin=task.asin,
        )
        _update_progress(
            task, session, 4, "rendering", 80, f"报告已生成 ({len(insights_md or '')} 字)"
        )

        # Phase 5
        _update_progress(task, session, 5, "rendering", 85, "正在渲染可视化看板...")
        from src.config import config as engine_config
        from src.output_manager import generate_outputs

        tmpdate = datetime.now().strftime("%m.%d-%H:%M")
        run_dir = Path(settings.OUTPUT_DIR) / f"{task.asin}-{tmpdate}"
        run_dir.mkdir(parents=True, exist_ok=True)
        engine_config.OUTPUT_DIR = run_dir
        engine_config.MAX_REVIEWS = max_reviews
        outputs = generate_outputs(
            {
                "asin": task.asin,
                "total_reviews": len(tagged_reviews),
                "personas": personas_data,
                "golden_samples": golden_samples_data,
                "insights_md": insights_md or "",
                "statistics": stats,
                "sentiment": stats.get("sentiment", {}),
                "avg_rating": stats.get("avg_rating", 0),
                "summary": {"total": len(tagged_reviews)},
            },
            {
                "template_name": template,
                "sync_feishu": False,
                "output_dir": str(engine_config.OUTPUT_DIR),
                "asin": task.asin,
                "creator": "Xing",
            },
        )
        # 从输出文件路径读取 HTML 内容
        html_content = None
        html_path = outputs.get("html_path")
        if html_path:
            html_content = Path(html_path).read_text(encoding="utf-8")

        session.add(
            AnalysisReport(
                task_id=task.id,
                insights_md=insights_md,
                stats=stats,
                html_content=html_content,
                template_name=template,
                md_word_count=len(insights_md or ""),
            )
        )
        session.commit()

        task.status = "done"
        task.progress = 100
        task.current_phase = 5
        task.phase_message = "分析完成"
        task.completed_at = datetime.now(UTC)
        session.commit()

        n_review = len(reviews_data)
        n_persona = len(personas_data)
        _publish_sse(
            task.id,
            "done",
            {
                "task_id": str(task.id),
                "status": "done",
                "total_reviews": n_review,
            },
        )
        return {"status": "done", "total_reviews": n_review, "persona_count": n_persona}

    except Exception as e:
        task = session.get(Task, task_uuid)
        if task:
            task.status = "failed"
            task.error_message = f"{type(e).__name__}: {e}"
            task.completed_at = datetime.now(UTC)
            session.commit()
            _publish_sse(task.id, "error", {"message": str(e)})
        if self.request.retries < self.max_retries and not isinstance(e, (ValueError, TypeError)):
            raise self.retry(exc=e)  # noqa: B904
        raise
    finally:
        session.close()


def _update_progress(task, session, phase, status, progress, message):
    task.current_phase = phase
    task.status = status
    task.progress = progress
    task.phase_message = message
    session.commit()
    _publish_sse(task.id, "progress", {"phase": phase, "message": message, "progress": progress})


def _get_csv_path(session, config, task_id):
    upload_id = config.get("upload_id")
    if upload_id:
        upload = session.get(Upload, UUID(upload_id))
        if upload:
            path = upload.stored_path
            # MinIO 路径: minio://bucket/object_key → 下载到本地临时文件
            if path.startswith("minio://"):
                return _download_from_minio(path)
            return path
    sample_csv = _ENGINE_ROOT / "examples" / "reviews_sample.csv"
    if sample_csv.exists():
        return str(sample_csv)
    raise FileNotFoundError("未找到 CSV 文件")


def _download_from_minio(minio_path: str) -> str:
    """从 MinIO 下载文件到临时目录，返回本地路径"""
    import tempfile

    from app.services.storage_service import storage_service

    # minio://bucket/object_key
    parts = minio_path.replace("minio://", "", 1).split("/", 1)
    object_key = parts[1] if len(parts) > 1 else parts[0]

    content = storage_service.get_file(object_key)
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name


def _load_reviews(csv_path, max_reviews):
    from src.data_loader import load_reviews_from_file

    reviews, _ = load_reviews_from_file(csv_path)
    if len(reviews) > max_reviews:
        reviews = reviews[:max_reviews]
    return reviews
