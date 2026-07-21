"""上传文件请求/响应 Schema"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """上传成功后的响应数据"""

    # 上传记录 ID
    upload_id: UUID
    # 原始文件名
    original_name: str
    # 文件大小（字节）
    size_bytes: int
    # CSV 中包含的有效评论条数
    review_count: int
    # 前 10 行预览（每行是一个 dict）
    preview_rows: list[dict]

    model_config = {"from_attributes": True}


class UploadRecord(BaseModel):
    """上传历史记录"""

    id: UUID
    original_name: str
    stored_path: str
    size_bytes: int
    review_count: int
    storage_backend: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadListResponse(BaseModel):
    """上传记录列表"""

    uploads: list[UploadRecord]
    total: int
