"""
MinIO 对象存储服务 — 文件上传、下载、删除、预签名 URL

文件实际存储在 MinIO 容器中，数据库只记录元数据（stored_path）。
"""

import uuid
from datetime import datetime
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    """MinIO 文件存储服务

    职责：管理 MinIO bucket，提供文件 CRUD 操作。
    不操作数据库 — 数据库操作由 task_service 或 upload_service 负责。
    """

    def __init__(self):
        # 创建 MinIO 客户端（内网通信不加密）
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def ensure_bucket(self) -> None:
        """确保存储桶存在，不存在则创建

        在 FastAPI startup 事件中调用。
        """
        bucket = settings.MINIO_BUCKET
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
            print(f"✓ MinIO bucket '{bucket}' 已创建")

    def upload_csv(self, file_content: bytes, original_name: str) -> tuple[str, str]:
        """上传 CSV 文件到 MinIO

        Args:
            file_content: 文件的二进制内容
            original_name: 用户上传时的原始文件名

        Returns:
            (object_key, stored_path): MinIO 对象键和完整存储路径
        """
        bucket = settings.MINIO_BUCKET

        # 生成唯一文件名，保留原始扩展名
        ext = ".csv"
        if "." in original_name:
            ext = original_name[original_name.rindex(".") :]

        # 按日期分目录存储: uploads/2026-07-19/uuid.csv
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        unique_name = f"{uuid.uuid4().hex}{ext}"
        object_key = f"uploads/{date_prefix}/{unique_name}"

        # 上传到 MinIO
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=BytesIO(file_content),
            length=len(file_content),
            content_type="text/csv",
        )

        # stored_path 是完整路径，方便后续读取
        stored_path = f"minio://{bucket}/{object_key}"
        return object_key, stored_path

    def get_file(self, object_key: str) -> bytes:
        """从 MinIO 下载文件内容

        Args:
            object_key: MinIO 中的对象键（如 uploads/2026-07-19/abc.csv）

        Returns:
            文件的二进制内容
        """
        bucket = settings.MINIO_BUCKET
        response = self.client.get_object(bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, object_key: str) -> bool:
        """从 MinIO 删除文件

        Args:
            object_key: MinIO 中的对象键

        Returns:
            是否删除成功
        """
        bucket = settings.MINIO_BUCKET
        try:
            self.client.remove_object(bucket, object_key)
            return True
        except S3Error:
            return False

    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """生成临时下载链接（预签名 URL）

        Args:
            object_key: MinIO 中的对象键
            expires: 链接有效期（秒），默认 1 小时

        Returns:
            可直接下载的临时 URL
        """
        bucket = settings.MINIO_BUCKET
        return self.client.presigned_get_object(bucket, object_key, expires=expires)


# 全局单例，所有模块共用同一个 MinIO 客户端
storage_service = StorageService()
