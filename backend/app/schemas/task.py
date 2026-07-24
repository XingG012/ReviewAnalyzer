"""
任务请求/响应 Schema

前后端校验规则必须与 Zod 端一致（见 frontend/src/lib/validators.ts）。
"""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskConfig(BaseModel):
    """任务分析配置（创建任务时的可选参数）"""

    # 分析评论数量上限（10-2000 条）
    max_reviews: int = Field(default=500, ge=10, le=2000)
    # 每批处理的评论数量（5-50 条/批）
    batch_size: int = Field(default=20, ge=20, le=50)
    # 可视化看板模板名
    template: str = Field(default="premium-gold")


class TaskCreate(BaseModel):
    """创建任务请求体"""

    # Amazon 商品 ASIN，必须 10 位大写字母数字
    asin: str = Field(min_length=10, max_length=10, description="Amazon 商品 ASIN")
    # 站点: US / UK / DE / JP
    site: Literal["US", "UK", "DE", "JP"] = "US"
    # 数据来源: csv / sorftime
    source: Literal["csv", "sorftime"] = "csv"
    # CSV 上传记录 ID（source=csv 时必填）
    upload_id: UUID | None = None
    # 可选分析配置（有默认值）
    config: TaskConfig = Field(default_factory=TaskConfig)

    @field_validator("asin")
    @classmethod
    def validate_asin(cls, v: str) -> str:
        """校验 ASIN 格式：10 位大写字母数字"""
        if not re.match(r"^[A-Z0-9]{10}$", v.upper()):
            raise ValueError("ASIN 格式不正确，应为 10 位字母数字组合")
        return v.upper()


class TaskResponse(BaseModel):
    """任务响应体"""

    id: UUID
    asin: str
    site: str
    source: str
    status: str
    progress: int
    current_phase: int
    phase_message: str | None = None
    config: dict
    total_reviews: int
    persona_count: int
    avg_rating: float | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """任务列表响应体"""

    tasks: list[TaskResponse]
    total: int
