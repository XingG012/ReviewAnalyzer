"""
用户画像 + 黄金样本模型

Persona:      personas 表 — AI 基于「场景 × 性别」交叉识别的典型用户群体
GoldenSample: golden_samples 表 — 每个画像最具代表性的 3 正 + 3 负评论

关系: Task 1 ── N Persona 1 ── N GoldenSample N ── 1 Review
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid

if TYPE_CHECKING:
    from app.models.task import Task


class Persona(Base, TimestampMixin):
    """用户画像 — 一组具有相同使用场景和性别特征的用户群体"""

    __tablename__ = "personas"

    # 主键
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # 外键 → tasks
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 画像名称，如 "家用_女性"、"户外_男性"
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 该画像覆盖的评论人数
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 交叉维度名，如 "场景_性别"
    dimension: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 画像特征标签
    # 示例: {"场景": "家用", "性别": "女性", "年龄段": "25-35"}
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 前端展示颜色（hex），每个画像用不同颜色区分
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")

    # AI 生成的画像一句话概括
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 关联关系 ──
    task: Mapped["Task"] = relationship("Task", back_populates="personas")

    # 一个画像包含多条黄金样本
    golden_samples: Mapped[list["GoldenSample"]] = relationship(
        "GoldenSample", back_populates="persona", cascade="all, delete-orphan"
    )


class GoldenSample(Base, TimestampMixin):
    """黄金样本 — 画像中最具代表性的评论摘录"""

    __tablename__ = "golden_samples"

    # 主键
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # 外键 → tasks（冗余，加速查询）
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 外键 → personas（属于哪个画像）
    persona_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 外键 → reviews（指向具体评论）
    review_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 情感标签: positive / negative
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 更细粒度的情感分类
    sentiment_class: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 关联回 Persona
    persona: Mapped["Persona"] = relationship("Persona", back_populates="golden_samples")
