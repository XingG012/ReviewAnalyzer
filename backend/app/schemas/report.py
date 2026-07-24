"""
报告响应 Schema

前后端校验规则与 Zod 端一致。
"""

from datetime import datetime

from pydantic import BaseModel


class ReportResponse(BaseModel):
    """分析报告完整响应 — 包含 Phase 4-5 全部产物"""

    insights_md: str | None = None
    stats: dict | None = None
    chart_configs: dict | None = None
    html_content: str | None = None
    template_name: str
    created_at: datetime

    model_config = {"from_attributes": True}
