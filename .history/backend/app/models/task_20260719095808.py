"""
分析任务模型 — tasks 表

一个 Task 代表用户提交的一次分析请求。
生命周期: pending → fetching → tagging → analyzing → rendering → done
任何阶段出错 → failed
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,  # 数据库层 CHECK 约束，杜绝非法数据写入
    DateTime,
    Float,
    Integer,
    SmallInteger,  # 小整数，节省存储（progress 0-100 不需要 4 字节）
    String,
    Text,  # 不限长度的文本字段
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid

# TYPE_CHECKING 块：仅类型检查时导入，运行时不会循环引用
# 因为 Persona/Report/Review 也 import 了 Task，直接 import 会死循环
if TYPE_CHECKING:
    from app.models.persona import Persona
    from app.models.report import AnalysisReport
    from app.models.review import Review


class Task(Base, TimestampMixin):
    """分析任务 — 记录一次完整 5 Phase 分析的全部状态"""

    # __tablename__ 指定 PostgreSQL 中实际的表名
    __tablename__ = "tasks"

    # ── 主键 ──
    # UUID(as_uuid=True) → 数据库存 native UUID 类型，不是字符串
    # default=gen_uuid → 新建时自动生成随机 UUID
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # ── 输入信息 ──
    # Amazon 商品 ASIN，10 位字母数字，如 B0DGV4T6BK
    asin: Mapped[str] = mapped_column(String(20), nullable=False)

    # 亚马逊站点代码: US / UK / DE / JP
    site: Mapped[str] = mapped_column(String(5), nullable=False, default="US")

    # 数据来源: csv（用户上传） / sorftime（API 对接）
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="csv")

    # ── 运行状态 ──
    # 7 种状态: pending / fetching / tagging / analyzing / rendering / done / failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # 总体进度 0-100，由 Celery Worker 在每个 Phase 完成后更新
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # 当前阶段编号 1-5，0 表示尚未开始
    current_phase: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # 当前阶段的中文描述，如"正在 AI 打标中... (47/100)"，用于 SSE 推送
    phase_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 配置快照 ──
    # JSONB 存储创建任务时的完整配置，方便复现
    # 示例: {"max_reviews": 500, "batch_size": 20, "template": "premium-gold"}
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ── 结果摘要（冗余字段，避免每次都 JOIN 查统计） ──
    # 本任务分析的评论总数
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 识别出的用户画像数量（通常 ≤ 4）
    persona_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 所有评论的平均分（1-5 星）
    avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 时间戳 ──
    # 分析实际开始执行的时间（Celery Worker 接手时设置）
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 分析完成（done 或 failed）的时间
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── 错误信息 ──
    # 失败时的错误描述，如"Phase 2 AI 打标超时"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 在哪个 Phase 失败的（1-5）
    error_phase: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # ── 关联关系 ──
    # cascade="all, delete-orphan" → 删除 Task 时自动删除所有关联的评论/画像/报告
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="task", cascade="all, delete-orphan"
    )
    personas: Mapped[list["Persona"]] = relationship(
        "Persona", back_populates="task", cascade="all, delete-orphan"
    )
    # uselist=False → 一对一关系，每个 Task 最多一份报告
    report: Mapped[Optional["AnalysisReport"]] = relationship(
        "AnalysisReport",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ── 数据库层约束 ──
    # CHECK 约束在数据库层兜底，即使代码 bug 也不会写入非法值
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','fetching','tagging','analyzing','rendering','done','failed')",
            name="chk_tasks_status",
        ),
        CheckConstraint("source IN ('csv','sorftime')", name="chk_tasks_source"),
        CheckConstraint("site IN ('US','UK','DE','JP')", name="chk_tasks_site"),
        CheckConstraint("progress BETWEEN 0 AND 100", name="chk_tasks_progress"),
    )
