"""
原始评论 + AI 打标结果模型

Review:      reviews 表 — 存储从 CSV / Sorftime 获取的原始评论数据
TaggedReview: tagged_reviews 表 — 存储 AI 分析后的 22 维标签 + 情感 + 信息评分

关系: Task 1 ── N Review 1 ── 1 TaggedReview（每条评论最多一条打标结果）
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,  # 布尔类型: 是否已验证购买
    Date,  # 日期类型: 评论日期
    Float,  # 浮点数: 评分
    ForeignKey,  # 外键约束
    Integer,  # 整数: helpful_count
    SmallInteger,  # 小整数: info_score
    String,  # 变长字符串
    Text,  # 不限长文本: body
    UniqueConstraint,  # 唯一约束: 同一任务下 review_id 不重复
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid

if TYPE_CHECKING:
    from app.models.task import Task


class Review(Base, TimestampMixin):
    """原始评论 — 存储从 CSV 导入或 API 获取的原始数据"""

    __tablename__ = "reviews"

    # 主键
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # 外键 → tasks 表
    # ondelete="CASCADE" → 删除任务时自动删除该任务下所有评论
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # 创建 B-tree 索引，加速按 task_id 查询
    )

    # ── Amazon 评论原始字段 ──
    # Amazon 平台分配的评论 ID（如 R3ABC123），可能为空
    review_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 评论标题（Amazon 上用户可选的标题行）
    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 评论正文（必填字段）
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # 星级评分 1.0-5.0
    rating: Mapped[float] = mapped_column(Float, nullable=False)

    # 评论者昵称
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 评论发布日期
    date: Mapped[str | None] = mapped_column(Date, nullable=True)

    # 该评论被多少人点了"有帮助"
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)

    # 是否为已验证购买（Verified Purchase 标签）
    verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)

    # 评论附带的图片 URL 列表，JSONB 存储: ["https://...jpg", "https://...png"]
    images: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 商品变体信息（如颜色、尺寸）
    variant: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 评论来源站点（如 com / co.uk / de）
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── 关联关系 ──
    # back_populates 和 Task.reviews 形成双向关联
    task: Mapped["Task"] = relationship("Task", back_populates="reviews")

    # 一对一到 TaggedReview（uselist=False）
    tagged: Mapped[Optional["TaggedReview"]] = relationship(
        "TaggedReview",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ── 约束 ──
    # 同一任务下 Amazon review_id 不可重复
    __table_args__ = (UniqueConstraint("task_id", "review_id", name="uq_reviews_task_review"),)


class TaggedReview(Base, TimestampMixin):
    """AI 打标结果 — 存储 Claude 分析的 22 维标签 + 情感 + 信息评分"""

    __tablename__ = "tagged_reviews"

    # 主键
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # 外键 → tasks
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 外键 → reviews（一对一关联原始评论）
    review_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── AI 分析结果 ──
    # 情感标签: 积极 / 中性 / 消极
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 信息价值评分 0-10，判断这条评论对决策有多大参考价值
    info_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # 22 维标签，JSONB 存储
    # 示例: {"人群_性别": "女性", "人群_年龄段": "25-35岁", "使用_场景": "家用", ...}
    # GIN 索引（alembic 迁移中创建）加速标签过滤查询
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 关联回 Review
    review: Mapped["Review"] = relationship("Review", back_populates="tagged")
