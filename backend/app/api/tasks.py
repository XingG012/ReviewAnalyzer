"""
任务 CRUD API

POST   /api/tasks              — 创建分析任务
GET    /api/tasks              — 查询任务列表（分页+筛选）
GET    /api/tasks/{id}         — 查询任务详情
DELETE /api/tasks/{id}         — 删除任务
POST   /api/tasks/{id}/retry   — 重试失败任务
GET    /api/tasks/{id}/stream  — SSE 实时进度推送
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse
from app.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TaskResponse:
    return await task_service.create_task(db, data)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TaskListResponse:
    return await task_service.list_tasks(db, status=status, offset=offset, limit=limit)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TaskResponse:
    return await task_service.get_task(db, task_id)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    await task_service.delete_task(db, task_id)


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TaskResponse:
    return await task_service.retry_task(db, task_id)


@router.get("/{task_id}/stream")
async def stream_task_progress(task_id: UUID):
    """SSE 实时进度推送 — 直接异步读 Redis PubSub

    浏览器: const es = new EventSource('/api/tasks/{id}/stream')
    """

    async def event_generator():
        import json as _json

        import redis.asyncio as aioredis

        r = aioredis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"task:{task_id}")
        await pubsub.get_message(timeout=0.1)  # 清掉订阅确认消息

        # 发送连接确认
        yield f"data: {_json.dumps({'event': 'connected', 'task_id': str(task_id)})}\n\n"

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = _json.loads(message["data"])
                event = payload.get("event", "message")
                data = payload.get("data", {})
                yield f"event: {event}\ndata: {_json.dumps(data)}\n\n"
        except Exception:
            pass
        finally:
            await pubsub.unsubscribe(f"task:{task_id}")
            await r.aclose()  # type: ignore[attr-defined]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
