"""
Celery 应用实例 — 分析任务的异步执行引擎

启动命令: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
"""

from celery import Celery

from app.core.config import settings

# 创建 Celery 实例
# broker: 任务消息存放处（Redis）
# backend: 任务结果存放处（Redis）
celery_app = Celery(
    "review_analyzer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 全局配置
celery_app.conf.update(
    # 序列化格式
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务追踪
    task_track_started=True,
    # 可靠性：任务完成后 ACK（防止 worker 崩溃丢任务）
    task_acks_late=True,
    # Worker 丢失时任务重新入队
    task_reject_on_worker_lost=True,
    # 超时配置（分析任务最长 15 分钟）
    task_soft_time_limit=900,  # 软超时：抛出异常，可捕获清理
    task_time_limit=1200,  # 硬超时：强制 kill
    # 每次只取一个任务（长任务公平分发）
    worker_prefetch_multiplier=1,
    # 重试策略
    task_default_retry_delay=60,
    task_max_retries=3,
)

# 自动发现任务模块
# 显式导入任务模块（确保 Worker 能发现任务）
import app.tasks.analysis_task  # noqa: E402, F401
