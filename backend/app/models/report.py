"""
分析报告模型 — analysis_reports 表

一个 Task 对应唯一一份报告（task_id 有 UNIQUE 约束）。
存储 Phase 4 生成的 14 章 Markdown 洞察报告 + 统计数据 + Chart.js 图表配置。
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid

if TYPE_CHECKING:
    from app.models.task import Task


class AnalysisReport(Base, TimestampMixin):
    """分析报告 — Phase 4-5 产物的持久化"""

    __tablename__ = "analysis_reports"

    # 主键
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # 外键 → tasks（UNIQUE 确保一个任务只有一份报告）
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 一对一关系
        index=True,
    )

    # ── Phase 4 产物 ──
    # 14 章 Markdown 洞察报告全文（可能数万字）
    insights_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 统计数据快照
    # 示例: {"total_reviews": 500, "avg_rating": 4.2, "sentiment": {...}, ...}
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 战略数据
    # 示例: {"moat": [...], "weakness": [...], "action_matrix": [...]}
    strategic_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Chart.js 图表配置（前端 react-chartjs-2 直接消费）
    # 示例: {"sentiment_pie": {...}, "tags_radar": {...}, ...}
    chart_configs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 渲染后的完整 HTML 看板（内嵌 CSS + Chart.js CDN）
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 元数据 ──
    # 使用的可视化模板: premium-gold / dark-tech / linear-minimal / ...
    template_name: Mapped[str] = mapped_column(String(50), nullable=False, default="premium-gold")

    # Markdown 报告字数
    md_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 关联回 Task
    task: Mapped["Task"] = relationship("Task", back_populates="report")
