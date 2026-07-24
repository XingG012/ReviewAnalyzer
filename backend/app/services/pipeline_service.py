"""
分析流水线服务 — 触发 Celery 异步任务

职责：接收 HTTP 请求，启动 Celery 任务，立即返回。
"""

from uuid import UUID

from app.tasks.analysis_task import run_analysis_pipeline


class PipelineService:
    """分析流水线编排器

    不直接执行分析 — 只负责将任务放入 Celery 队列。
    分析逻辑在 app/tasks/analysis_task.py 中。
    """

    def start_analysis(self, task_id: UUID) -> None:
        """启动异步分析任务

        Args:
            task_id: 待分析的任务 UUID
        """
        # delay() 将任务发送到 Celery broker (Redis)
        # Celery Worker 异步取走执行，HTTP 请求不阻塞
        run_analysis_pipeline.delay(str(task_id))


# 全局单例
pipeline_service = PipelineService()
