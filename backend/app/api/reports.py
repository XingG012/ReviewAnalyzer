"""
报告查询 API

GET /api/tasks/{task_id}/report — 查询分析报告（JSON 格式）
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.report import ReportResponse
from app.services.review_service import review_service

router = APIRouter()


@router.get("/{task_id}/report", response_model=ReportResponse)
async def get_report(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ReportResponse:
    """查询任务的完整分析报告

    仅 done 状态返回报告；其他状态返回 404。
    """
    return await review_service.get_report(db, task_id)
