"""
评论数据查询 API

GET /api/tasks/{task_id}/reviews  — 原始评论分页查询（支持评分筛选）
GET /api/tasks/{task_id}/tagged   — AI 打标结果分页查询（支持标签筛选）
GET /api/tasks/{task_id}/personas — 用户画像 + 黄金样本查询
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.persona import PersonaResponse
from app.schemas.review import ReviewListResponse, TaggedReviewListResponse
from app.services.review_service import review_service

router = APIRouter()


@router.get("/{task_id}/reviews", response_model=ReviewListResponse)
async def get_reviews(
    task_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    rating_min: float | None = Query(None, ge=1.0, le=5.0),
    rating_max: float | None = Query(None, ge=1.0, le=5.0),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ReviewListResponse:
    """分页查询原始评论，支持评分范围筛选"""
    return await review_service.get_reviews(
        db, task_id,
        offset=offset, limit=limit,
        rating_min=rating_min, rating_max=rating_max,
    )


@router.get("/{task_id}/tagged", response_model=TaggedReviewListResponse)
async def get_tagged_reviews(
    task_id: UUID,
    tag_key: str | None = Query(None, description="标签维度名，如 '人群_性别'"),
    tag_value: str | None = Query(None, description="标签值，如 '女性'"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TaggedReviewListResponse:
    """分页查询 AI 打标结果，支持按 22 维标签筛选"""
    return await review_service.get_tagged_reviews(
        db, task_id,
        tag_key=tag_key, tag_value=tag_value,
        offset=offset, limit=limit,
    )


@router.get("/{task_id}/personas", response_model=list[PersonaResponse])
async def get_personas(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PersonaResponse]:
    """查询用户画像列表，包含每个画像的黄金样本"""
    return await review_service.get_personas(db, task_id)
