"""
用户画像响应 Schema

Persona 是 AI 基于「场景 × 性别」交叉识别的典型用户群体。
GoldenSample 是每个画像最具代表性的评论摘录。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GoldenSampleResponse(BaseModel):
    """黄金样本 — 画像中最具代表性的评论摘录"""

    id: UUID
    sentiment: str | None = None
    sentiment_class: str | None = None
    # 关联 Review 注入的字段
    review_body: str | None = None
    review_rating: float | None = None

    model_config = {"from_attributes": True}


class PersonaResponse(BaseModel):
    """用户画像 — 包含关联的黄金样本列表"""

    id: UUID
    task_id: UUID
    name: str
    count: int
    dimension: str | None = None
    tags: dict
    color: str
    summary: str | None = None
    golden_samples: list[GoldenSampleResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
