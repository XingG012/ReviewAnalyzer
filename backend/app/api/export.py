"""
文件导出 API

GET /api/tasks/{task_id}/export/csv  — 下载打标 CSV（UTF-8 BOM，Excel 友好）
GET /api/tasks/{task_id}/export/md   — 下载洞察报告 Markdown
GET /api/tasks/{task_id}/export/html — 下载可视化看板 HTML
"""

import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task

router = APIRouter()


async def _get_task(db: AsyncSession, task_id: UUID) -> Task:
    """辅助：获取任务并在必要时返回 404"""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


# ── CSV 导出 ──────────────────────────────────────────────

@router.get("/{task_id}/export/csv")
async def export_csv(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """导出打标数据为 CSV 文件（UTF-8 BOM 编码）

    动态从数据库生成，包含：原始评论列 + sentiment + info_score + 22 维标签列。
    """
    task = await _get_task(db, task_id)

    if task.status != "done":
        raise HTTPException(
            status_code=404,
            detail=f"报告尚未生成，无法导出。当前状态: {task.status}",
        )

    result = await db.execute(
        select(TaggedReview, Review.body, Review.rating, Review.author, Review.date)
        .join(Review, TaggedReview.review_id == Review.id)
        .where(TaggedReview.task_id == task_id)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="无打标数据可导出")

    # 收集所有标签维度（动态列）
    all_tag_keys: list[str] = []
    seen_keys: set[str] = set()
    for tr, *_ in rows:
        for key in tr.tags:
            if key not in seen_keys:
                seen_keys.add(key)
                all_tag_keys.append(key)

    fixed_columns = ["review_id", "body", "rating", "author", "date", "sentiment", "info_score"]
    all_columns = fixed_columns + all_tag_keys

    output = StringIO()
    output.write("﻿")  # UTF-8 BOM — Excel 正确识别中文
    writer = csv.DictWriter(output, fieldnames=all_columns, extrasaction="ignore")
    writer.writeheader()

    for tr, body, rating, author, date in rows:
        row_data = {
            "review_id": str(tr.review_id),
            "body": body,
            "rating": rating,
            "author": author,
            "date": str(date) if date else "",
            "sentiment": tr.sentiment,
            "info_score": tr.info_score,
        }
        for key in all_tag_keys:
            row_data[key] = tr.tags.get(key, "")
        writer.writerow(row_data)

    csv_content = output.getvalue()

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{task.asin}_tagged.csv"',
        },
    )


# ── Markdown 导出 ─────────────────────────────────────────

@router.get("/{task_id}/export/md")
async def export_md(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """导出 14 章洞察报告为 Markdown 文件"""
    task = await _get_task(db, task_id)

    if task.status != "done":
        raise HTTPException(
            status_code=404,
            detail=f"报告尚未生成，无法导出。当前状态: {task.status}",
        )

    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.task_id == task_id)
    )
    report = result.scalar_one_or_none()

    if report is None or not report.insights_md:
        raise HTTPException(status_code=404, detail="洞察报告内容为空")

    return Response(
        content=report.insights_md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{task.asin}_report.md"',
        },
    )


# ── HTML 导出 ─────────────────────────────────────────────

@router.get("/{task_id}/export/html")
async def export_html(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """导出可视化看板为独立 HTML 文件"""
    task = await _get_task(db, task_id)

    if task.status != "done":
        raise HTTPException(
            status_code=404,
            detail=f"报告尚未生成，无法导出。当前状态: {task.status}",
        )

    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.task_id == task_id)
    )
    report = result.scalar_one_or_none()

    if report is None or not report.html_content:
        raise HTTPException(status_code=404, detail="HTML 看板内容为空")

    return Response(
        content=report.html_content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{task.asin}_dashboard.html"',
        },
    )
