"""
全局配置管理 — 基于 pydantic-settings，从 .env 和环境变量读取所有配置项
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ReviewAnalyzer 全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://review:review@localhost:5432/reviewanalyzer"

    # ── Redis / Celery ──
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ── MinIO ──
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "review-analyzer"
    MINIO_SECURE: bool = False

    # ── AI 引擎 ──
    CLI_ENGINE: str = "claude"  # claude / opencode / none
    CLI_TIMEOUT: int = 600  # 单次 CLI 调用超时（秒）
    MAX_CONCURRENT_AGENTS: int = 4  # 并发批次数上限

    # ── 应用 ──
    APP_ENV: str = "development"
    LOG_LEVEL: str = "info"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
