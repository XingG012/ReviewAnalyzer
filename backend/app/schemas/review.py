"""
评论请求/响应 Schema

包含原始评论 Review 和 AI 打标结果 TaggedReview 的 API 响应格式。
"""

import datetime as _dt
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReviewResponse(BaseModel):
    """原始评论响应"""

    id: UUID
    task_id: UUID
    review_id: str | None = None
    title: str | None = None
    body: str
    rating: float
    author: str | None = None
    date: _dt.date | None = None
    helpful_count: int
    verified_purchase: bool
    images: list | None = None
    variant: str | None = None
    country: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    """原始评论分页列表"""

    reviews: list[ReviewResponse]
    total: int


class TaggedReviewResponse(BaseModel):
    """AI 打标结果响应 — 包含原始评论正文用于前端展示"""

    id: UUID
    task_id: UUID
    review_id: UUID
    sentiment: str | None = None
    info_score: int
    tags: dict
    # 关联查询时注入的原始评论字段
    review_body: str | None = None
    review_rating: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaggedReviewListResponse(BaseModel):
    """打标评论分页列表"""

    tagged_reviews: list[TaggedReviewResponse]
    total: int
