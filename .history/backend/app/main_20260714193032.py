"""
ReviewAnalyzer API — FastAPI 应用入口

Backend 三层架构:
  api/      → 路由 + 参数校验（仅此而已，禁止业务逻辑）
  services/ → 业务逻辑编排 + 数据库 CRUD
  models/   → 表结构定义 + 关系映射
"""

# 从标准库导入异步生成器类型，用于给生命周期函数做类型注解
from collections.abc import AsyncGenerator
# 从标准库导入异步上下文管理器装饰器，用来定义应用的启动/关闭生命周期
from contextlib import asynccontextmanager

# 导入 FastAPI 主类，是整个后端应用的核心入口
from fastapi import FastAPI
# 导入 CORS 跨域中间件，解决前后端分离时浏览器的跨域请求限制
from fastapi.middleware.cors import CORSMiddleware

# 导入项目汇总的总路由对象，所有业务接口都注册在这个路由里
from app.api.router import api_router
# 导入全局配置对象，统一管理所有环境变量和应用参数
from app.core.config import settings


@asynccontextmanager  # 装饰器作用：把下面的函数变成异步上下文管理器
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期：启动时初始化，关闭时清理"""
    # ========== 应用启动阶段（服务接收请求之前执行） ==========
    # 后续可在这里添加：初始化数据库连接池、加载AI模型、预热缓存等
    yield  # 分界线：yield 之前是启动逻辑，之后是关闭逻辑
    # ========== 应用关闭阶段（服务停止之前执行） ==========
    # 后续可在这里添加：关闭数据库连接、清理临时文件、刷新日志落盘等


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用（应用工厂设计模式）"""
    # 实例化 FastAPI 应用对象，配置基础元信息和生命周期
    app = FastAPI(
        title="ReviewAnalyzer API",       # 应用名称，会显示在自动生成的 Swagger 文档标题
        description="Amazon 评论深度分析平台 — 全栈版 v2.0",  # 应用描述，显示在文档首页
        version="2.0.0",                   # 应用版本号
        lifespan=lifespan,                 # 绑定生命周期管理器，接管启动/关闭逻辑
    )

    # 给应用挂载 CORS 跨域中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,  # 允许发起跨域请求的前端域名，从配置文件读取
        allow_credentials=True,               # 允许跨域请求携带 Cookie、认证凭证
        allow_methods=["*"],                  # 允许所有 HTTP 方法（GET/POST/PUT/DELETE 等）
        allow_headers=["*"],                  # 允许所有自定义请求头
    )

    # 定义健康检查接口：供 Docker 健康检查、负载均衡器探活使用
    @app.get("/api/health")
    async def health_check():
        """健康检查端点 — 供 Docker / 负载均衡器探测"""
        # 返回服务状态和版本，调用方通过 HTTP 状态码 + 返回值判断服务是否正常
        return {"status": "ok", "version": "2.0.0"}

    # 把总路由注册到应用上，统一添加 /api 前缀
    # 所有业务接口的路径都会自动变成 /api/xxx 的形式
    app.include_router(api_router, prefix="/api")

    # 返回配置完成的应用实例
    return app


# 调用工厂函数，创建全局的 app 实例
# uvicorn 启动服务时，会加载这个 app 对象作为服务入口
app = create_app()