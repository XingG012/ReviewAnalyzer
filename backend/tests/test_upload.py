"""文件上传 API 测试"""

import csv
import io
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.upload import Upload


def create_test_csv(num_rows: int = 10) -> bytes:
    """生成一个测试 CSV 文件（内存中）"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["review_id", "body", "rating", "author", "date"])
    for i in range(num_rows):
        writer.writerow(
            [f"R{i:04d}", f"这是一条测试评论内容_{i}", f"{3 + (i % 3)}.0", f"用户{i}", "2026-07-15"]
        )
    return output.getvalue().encode("utf-8")


class TestUploadCsv:
    """POST /api/upload/csv"""

    def test_upload_valid_csv(self, client: TestClient, db: Session):
        """上传有效 CSV → 201 + 预览数据"""
        csv_content = create_test_csv(10)

        # Mock MinIO 上传（避免依赖 MinIO 容器）
        with patch(
            "app.services.storage_service.storage_service.upload_csv",
            return_value=("test/key.csv", "minio://bucket/test/key.csv"),
        ):
            response = client.post(
                "/api/upload/csv",
                files={"file": ("test_reviews.csv", csv_content, "text/csv")},
            )

        assert response.status_code == 201
        data = response.json()
        assert "upload_id" in data
        assert data["original_name"] == "test_reviews.csv"
        assert data["review_count"] == 10
        assert len(data["preview_rows"]) == 10
        assert data["preview_rows"][0]["body"] == "这是一条测试评论内容_0"

    def test_upload_non_csv_file(self, client: TestClient):
        """上传非 CSV 文件 → 400"""
        response = client.post(
            "/api/upload/csv",
            files={"file": ("test.txt", b"not a csv", "text/plain")},
        )
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_upload_empty_file(self, client: TestClient):
        """上传空文件 → 400"""
        with patch(
            "app.services.storage_service.storage_service.upload_csv",
            return_value=("test/key.csv", "minio://bucket/test/key.csv"),
        ):
            response = client.post(
                "/api/upload/csv",
                files={"file": ("empty.csv", b"", "text/csv")},
            )
        assert response.status_code == 400
        assert "空" in response.json()["detail"]

    def test_upload_file_too_large(self, client: TestClient):
        """上传超过 50MB 文件 → 400"""
        # 生成大于 50MB 的假数据
        large_content = b"a" * (50 * 1024 * 1024 + 1)
        response = client.post(
            "/api/upload/csv",
            files={"file": ("huge.csv", large_content, "text/csv")},
        )
        assert response.status_code == 400
        assert "50MB" in response.json()["detail"]

    def test_upload_csv_with_no_valid_reviews(self, client: TestClient):
        """上传只有表头没有数据的 CSV → 400"""
        csv_content = b"review_id,body,rating,author,date\n"
        with patch(
            "app.services.storage_service.storage_service.upload_csv",
            return_value=("test/key.csv", "minio://bucket/test/key.csv"),
        ):
            response = client.post(
                "/api/upload/csv",
                files={"file": ("header_only.csv", csv_content, "text/csv")},
            )
        assert response.status_code == 400
        assert "评论" in response.json()["detail"]


class TestUploadHistory:
    """Upload 记录 CRUD 验证 — 通过同步 DB 直接测试（async HTTP 端点见 Step 6）"""

    def test_insert_and_query(self, db: Session):
        """插入上传记录后可直接查询"""
        u1 = Upload(
            original_name="file1.csv",
            stored_path="minio://bucket/path1.csv",
            size_bytes=1024,
            review_count=100,
        )
        u2 = Upload(
            original_name="file2.csv",
            stored_path="minio://bucket/path2.csv",
            size_bytes=2048,
            review_count=200,
        )
        db.add_all([u1, u2])
        db.commit()

        # 验证刚才插入的记录可查询到（DB 中可能已有其他测试的数据）
        our_uploads = (
            db.query(Upload).filter(Upload.original_name.in_(["file1.csv", "file2.csv"])).all()
        )
        assert len(our_uploads) == 2

    def test_default_values(self, db: Session):
        """默认值正确"""
        u = Upload(
            original_name="test.csv",
            stored_path="minio://bucket/test.csv",
        )
        db.add(u)
        db.commit()

        assert u.size_bytes == 0
        assert u.review_count == 0
        assert u.storage_backend == "minio"
        assert u.created_at is not None


class TestStorageService:
    """storage_service 单元测试"""

    def test_upload_csv_raw(self):
        """测试上传逻辑（mock MinIO 客户端）"""
        from app.services.storage_service import storage_service

        test_bytes = create_test_csv(5)
        with patch.object(storage_service.client, "put_object") as mock_put:
            object_key, stored_path = storage_service.upload_csv(test_bytes, "reviews.csv")

        assert object_key.startswith("uploads/")
        assert object_key.endswith(".csv")
        assert stored_path.startswith("minio://")
        mock_put.assert_called_once()
