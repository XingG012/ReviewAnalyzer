"""路由汇总 — 将所有子路由注册到同一 prefix 下"""

from fastapi import APIRouter

from app.api import export, reports, reviews, tasks, upload

api_router = APIRouter()

api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(reviews.router, prefix="/tasks", tags=["reviews"])
api_router.include_router(reports.router, prefix="/tasks", tags=["reports"])
api_router.include_router(export.router, prefix="/tasks", tags=["export"])
