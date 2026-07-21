"""
文件上传 API

POST /api/upload/csv     — 上传 CSV 到 MinIO，解析评论数量，记录数据库
GET  /api/upload/history  — 查询历史上传记录
"""

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.upload import Upload
from app.schemas.upload import UploadListResponse, UploadRecord, UploadResponse
from app.services.storage_service import storage_service

router = APIRouter()

# 文件大小上限 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/csv", response_model=UploadResponse, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),  # noqa: B008 (FastAPI 要求)
    db: AsyncSession = Depends(get_db),  # noqa: B008 (FastAPI 要求)
) -> UploadResponse:
    """上传 CSV 评论文件

    流程: 校验 → 上传 MinIO → 解析 CSV → 写入数据库 → 返回预览
    """
    # ── 校验文件类型 ──
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="请上传 CSV 格式的文件")

    # 读取文件内容到内存
    content = await file.read()

    # 校验文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 50MB")

    # 校验非空
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件为空，请检查后重试")

    # ── 上传到 MinIO 对象存储 ──
    # object_key 是 MinIO 内部路径，stored_path 是完整标识符存入数据库
    object_key, stored_path = storage_service.upload_csv(
        file_content=content,
        original_name=file.filename or "unknown.csv",
    )

    # ── 使用 pandas 解析 CSV，统计评论条数 + 取前 10 行预览 ──
    try:
        df = pd.read_csv(BytesIO(content))
        review_count = len(df)
        # fillna("") 把 NaN 转为空字符串，避免 JSON 序列化报错
        preview_rows = df.head(10).fillna("").to_dict(orient="records")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"CSV 文件解析失败：{e}",
        ) from e

    if review_count == 0:
        raise HTTPException(
            status_code=400,
            detail="文件中没有找到有效评论，请检查 CSV 内容",
        )

    # ── 写入数据库记录 ──
    upload_record = Upload(
        original_name=file.filename or "unknown.csv",
        stored_path=stored_path,
        size_bytes=len(content),
        review_count=review_count,
    )
    db.add(upload_record)
    await db.commit()
    await db.refresh(upload_record)

    return UploadResponse(
        upload_id=upload_record.id,
        original_name=upload_record.original_name,
        size_bytes=upload_record.size_bytes,
        review_count=upload_record.review_count,
        preview_rows=preview_rows,
    )


@router.get("/history", response_model=UploadListResponse)
async def list_uploads(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),  # noqa: B008 (FastAPI 要求)
) -> UploadListResponse:
    """查询历史上传记录，按时间倒序"""
    # 查询总数
    total_query = select(func.count()).select_from(Upload)
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # 查询列表
    query = select(Upload).order_by(Upload.created_at.desc()).limit(limit)
    result = await db.execute(query)
    uploads = result.scalars().all()

    return UploadListResponse(
        uploads=[UploadRecord.model_validate(u) for u in uploads],
        total=total,
    )
