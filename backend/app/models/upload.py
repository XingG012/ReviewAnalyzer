"""
上传文件记录模型 — uploads 表

用户每次上传 CSV 文件，数据库记录一条元数据。
文件实际内容存储在 MinIO 对象存储中，stored_path 是 MinIO 的 object key。
"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class Upload(Base, TimestampMixin):
    """上传文件记录 — 记录 CSV 文件的元数据，实际文件在 MinIO"""

    __tablename__ = "uploads"

    # 主键
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)

    # 用户上传时的原始文件名（如 "B0DGV4T6BK_reviews.csv"）
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)

    # MinIO 中的存储路径（object key）
    # 格式: "uploads/2026-07-19/uuid.csv"
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    # 文件大小（字节），BigInteger 支持最大约 9EB
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # CSV 中包含的有效评论条数（上传时解析统计）
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 存储后端: minio（默认）/ local（开发阶段兼容）
    storage_backend: Mapped[str] = mapped_column(String(20), nullable=False, default="minio")
