"""
SQLAlchemy 声明式基类 + 通用 Mixin

Base: 所有 ORM 模型继承的基类，SQLAlchemy 用它发现表结构
TimestampMixin: 混入类，给任意模型添加 created_at / updated_at 时间戳字段
gen_uuid(): 生成 UUID 主键的工具函数
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类

    所有模型类都必须继承 Base，Alembic 通过 Base.metadata 自动发现所有表。
    """

    pass


class TimestampMixin:
    """创建时间 + 更新时间 Mixin

    被其他模型类继承后，自动获得 created_at 和 updated_at 两个字段。
    数据库服务端默认值用 now()，Python 端用 datetime.now(UTC)。
    """

    # 记录创建时间
    # server_default=func.now() → 数据库层自动填当前时间
    # default=lambda: datetime.now(UTC) → Python 层也自动填（兼容 SQLite）
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # 记录最后更新时间
    # onupdate → 每次 UPDATE 时自动刷新为当前时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


def gen_uuid() -> uuid.UUID:
    """生成随机 UUID v4，作为每张表的主键默认值"""
    return uuid.uuid4()
