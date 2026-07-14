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
    # 启动时
    yield
    # 关闭时（各 Step 逐步添加清理逻辑）


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="ReviewAnalyzer API",
        description="Amazon 评论深度分析平台 — 全栈版 v2.0",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health_check():
        """健康检查端点 — 供 Docker / 负载均衡器探测"""
        return {"status": "ok", "version": "2.0.0"}

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
