"""
全局配置管理 — 基于 pydantic-settings，从 .env 和环境变量读取所有配置项
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ReviewAnalyzer 全局配置"""

    # 配置环境变量读取规则
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── 数据库 ──
    # 异步 PostgreSQL 完整连接地址，包含账号密码库名
    DATABASE_URL: str = "postgresql+asyncpg://review:review@localhost:5432/reviewanalyzer"

    # ── Redis / Celery 异步任务队列 ──
    # Celery 消息中间件地址，任务队列存放于 Redis 0 号库
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    # Celery 任务运行结果存储地址，复用 Redis 0 号库
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ── MinIO 对象存储（存 CSV、报告文件） ──
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "review-analyzer"
    MINIO_SECURE: bool = False

    # ── AI 引擎 ──
    # 选用的 AI 分析引擎，可选 claude / opencode / none
    CLI_ENGINE: str = "claude"
    CLI_TIMEOUT: int = 600
    MAX_CONCURRENT_AGENTS: int = 4

    # ── 应用基础配置 ──
    # 运行环境: development / production
    APP_ENV: str = "development"
    LOG_LEVEL: str = "info"
    # 允许跨域请求的前端地址列表
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


# 全局配置单例
settings = Settings()
