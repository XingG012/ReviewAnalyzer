"""
评论/报告查询服务 — Step 7 实现

职责：处理报告查询、评论分页筛选、画像查询等只读操作。
所有方法接收 AsyncSession，返回 Pydantic Schema 对象。
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.persona import Persona
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from app.schemas.persona import GoldenSampleResponse, PersonaResponse
from app.schemas.report import ReportResponse
from app.schemas.review import (
    ReviewListResponse,
    ReviewResponse,
    TaggedReviewListResponse,
    TaggedReviewResponse,
)


class ReviewService:
    """评论/报告查询服务 — 只读查询，供 API 层调用"""

    async def _get_task_or_404(self, db: AsyncSession, task_id: UUID) -> Task:
        """辅助：获取任务，不存在则 404"""
        task = await db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return task

    # ── 报告查询 ───────────────────────────────────────────

    async def get_report(self, db: AsyncSession, task_id: UUID) -> ReportResponse:
        """查询分析报告

        校验任务状态：只有 done 状态的任务才有可查询的报告。
        """
        task = await self._get_task_or_404(db, task_id)

        if task.status == "failed":
            raise HTTPException(status_code=404, detail="分析失败，无报告")
        if task.status != "done":
            raise HTTPException(
                status_code=404,
                detail=f"报告尚未生成，当前状态: {task.status}",
            )

        result = await db.execute(
            select(AnalysisReport).where(AnalysisReport.task_id == task_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=404, detail="报告尚未生成")

        return ReportResponse.model_validate(report)

    # ── 原始评论查询 ───────────────────────────────────────

    async def get_reviews(
        self,
        db: AsyncSession,
        task_id: UUID,
        offset: int = 0,
        limit: int = 50,
        rating_min: float | None = None,
        rating_max: float | None = None,
    ) -> ReviewListResponse:
        """分页查询原始评论，支持评分范围筛选"""
        await self._get_task_or_404(db, task_id)

        base = select(Review).where(Review.task_id == task_id)

        # 评分筛选
        if rating_min is not None:
            base = base.where(Review.rating >= rating_min)
        if rating_max is not None:
            base = base.where(Review.rating <= rating_max)

        # 总数
        count_query = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = base.order_by(Review.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        reviews = result.scalars().all()

        return ReviewListResponse(
            reviews=[ReviewResponse.model_validate(r) for r in reviews],
            total=total,
        )

    # ── 打标评论查询 ───────────────────────────────────────

    async def get_tagged_reviews(
        self,
        db: AsyncSession,
        task_id: UUID,
        tag_key: str | None = None,
        tag_value: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> TaggedReviewListResponse:
        """分页查询打标结果，支持标签维度筛选

        标签筛选在 Python 侧完成，因为 JSONB 字段路径查询在不同 SQLAlchemy
        版本间有差异，且单任务最大 2000 条，性能可接受。
        """
        await self._get_task_or_404(db, task_id)

        # JOIN TaggedReview + Review，一次查询获取打标结果和原始评论正文
        base = (
            select(TaggedReview, Review.body, Review.rating)
            .join(Review, TaggedReview.review_id == Review.id)
            .where(TaggedReview.task_id == task_id)
        )

        result = await db.execute(base)
        rows = result.all()  # list of (TaggedReview, body, rating)

        # Python 侧标签筛选
        if tag_key:
            rows = [
                (tr, body, rating)
                for tr, body, rating in rows
                if tr.tags.get(tag_key) == tag_value
            ]

        total = len(rows)

        # 分页
        page_rows = rows[offset : offset + limit]

        tagged_reviews = []
        for tr, body, rating in page_rows:
            tr_response = TaggedReviewResponse.model_validate(tr)
            tr_response.review_body = body
            tr_response.review_rating = float(rating) if rating is not None else None
            tagged_reviews.append(tr_response)

        return TaggedReviewListResponse(tagged_reviews=tagged_reviews, total=total)

    # ── 用户画像查询 ───────────────────────────────────────

    async def get_personas(self, db: AsyncSession, task_id: UUID) -> list[PersonaResponse]:
        """查询用户画像列表，包含每个画像的黄金样本（带评论正文）"""
        await self._get_task_or_404(db, task_id)

        # 查询所有画像（预加载 golden_samples）
        result = await db.execute(
            select(Persona)
            .where(Persona.task_id == task_id)
            .options(joinedload(Persona.golden_samples))
            .order_by(Persona.count.desc())
        )
        personas = result.unique().scalars().all()

        # 构建 persona_id → Review 的映射（批量查询，避免 N+1）
        response_list: list[PersonaResponse] = []
        for persona in personas:
            # 为每个画像批量获取其黄金样本关联的 Review
            sample_ids = [gs.review_id for gs in persona.golden_samples]
            review_map: dict[UUID, tuple[str, float]] = {}
            if sample_ids:
                reviews_result = await db.execute(
                    select(Review.id, Review.body, Review.rating).where(
                        Review.id.in_(sample_ids)
                    )
                )
                for rid, body, rating in reviews_result.all():
                    review_map[rid] = (body, float(rating) if rating else 0.0)

            # 构建 PersonaResponse
            persona_resp = PersonaResponse.model_validate(persona)
            persona_resp.golden_samples = []
            for gs in persona.golden_samples:
                gs_resp = GoldenSampleResponse.model_validate(gs)
                if gs.review_id in review_map:
                    gs_resp.review_body = review_map[gs.review_id][0]
                    gs_resp.review_rating = review_map[gs.review_id][1]
                persona_resp.golden_samples.append(gs_resp)

            response_list.append(persona_resp)

        return response_list


# 全局单例
review_service = ReviewService()
