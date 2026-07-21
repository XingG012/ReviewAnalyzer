"""
ReviewAnalyzer API — FastAPI 应用入口

Backend 三层架构:
  api/      → 路由 + 参数校验（仅此而已，禁止业务逻辑）
  services/ → 业务逻辑编排 + 数据库 CRUD
  models/   → 表结构定义 + 关系映射
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期：启动时初始化，关闭时清理"""
    # 启动阶段：初始化数据库迁移 + MinIO bucket
    from app.core.init_db import init_db
    from app.services.storage_service import storage_service

    init_db()
    storage_service.ensure_bucket()

    yield

    # 关闭阶段：可关闭连接、清理临时文件、刷新日志等


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用（工厂模式）"""
    app = FastAPI(
        title="ReviewAnalyzer API",
        description="Amazon 评论深度分析平台 — 全栈版 v2.0",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS 跨域中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 健康检查端点 — 供 Docker / 负载均衡器探测
    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "version": "2.0.0"}

    # 注册业务路由，统一加 /api 前缀
    app.include_router(api_router, prefix="/api")

    return app


# uvicorn 入口：app.main:app
app = create_app()
