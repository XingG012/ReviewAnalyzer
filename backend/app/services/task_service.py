"""
任务服务层 — Task CRUD 业务逻辑

职责：校验 → 数据库操作 → 返回 Schema 对象
禁止访问 HTTP Request/Response 对象。
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse


class TaskService:
    """分析任务 CRUD 服务

    所有方法接收 AsyncSession（由 FastAPI Depends 注入），
    返回 Pydantic Schema 对象（由 API 层序列化为 JSON）。
    """

    async def create_task(self, db: AsyncSession, data: TaskCreate) -> TaskResponse:
        """创建分析任务

        校验：source=csv 时 upload_id 必填 → 确认上传记录存在。
        创建 Task 记录，status=pending，等待 Celery 接手。
        """
        # 校验：CSV 模式下必须提供已上传的文件
        if data.source == "csv" and data.upload_id is None:
            raise HTTPException(
                status_code=400,
                detail="CSV 模式下需要先上传文件（upload_id）",
            )

        # upload_id 由前端刚刚上传获得，无需再次校验数据库

        # 创建 Task，默认状态 pending
        task = Task(
            asin=data.asin,
            site=data.site,
            source=data.source,
            status="pending",
            config={
                "max_reviews": data.config.max_reviews,
                "batch_size": data.config.batch_size,
                "template": data.config.template,
                "upload_id": str(data.upload_id) if data.upload_id else None,
            },
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        # 触发 Celery 异步分析任务（不阻塞 HTTP 响应）
        from app.services.pipeline_service import pipeline_service

        pipeline_service.start_analysis(task.id)

        return TaskResponse.model_validate(task)

    async def get_task(self, db: AsyncSession, task_id: UUID) -> TaskResponse:
        """查询单个任务详情"""
        task = await db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return TaskResponse.model_validate(task)

    async def list_tasks(
        self,
        db: AsyncSession,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> TaskListResponse:
        """分页查询任务列表，可按状态筛选"""
        # 基础查询
        query = select(Task)

        # 状态筛选
        if status:
            query = query.where(Task.status == status)

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询（按创建时间倒序）
        query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        tasks = result.scalars().all()

        return TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
        )

    async def delete_task(self, db: AsyncSession, task_id: UUID) -> None:
        """删除任务（级联删除关联的评论/画像/报告）

        运行中的任务不允许删除。
        """
        task = await db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 运行中的任务禁止删除
        if task.status == "running":
            raise HTTPException(
                status_code=409,
                detail="任务正在进行中，无法删除",
            )

        await db.delete(task)
        await db.commit()

    async def retry_task(self, db: AsyncSession, task_id: UUID) -> TaskResponse:
        """重试失败的任务：重置为 pending"""
        task = await db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 只有失败的任务可以重试
        if task.status != "failed":
            raise HTTPException(
                status_code=409,
                detail=f"只有失败的任务可以重试，当前状态: {task.status}",
            )

        # 重置状态
        task.status = "pending"
        task.progress = 0
        task.current_phase = 0
        task.error_message = None
        task.error_phase = None
        task.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(task)

        return TaskResponse.model_validate(task)
