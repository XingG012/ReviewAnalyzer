"""
全局配置管理 — 基于 pydantic-settings，从 .env 和环境变量读取所有配置项
"""
# 导入配置基类，用来定义所有环境配置字段
from pydantic_settings import BaseSettings, SettingsConfigDict

# 创建配置类，统一存放项目所有环境变量、连接地址、开关参数
class Settings(BaseSettings):
    """ReviewAnalyzer 全局配置"""

    # 配置读取规则
    model_config = SettingsConfigDict(
        env_file=".env",               # 指定读取本地 .env 文件中的配置
        env_file_encoding="utf-8",     # .env 文件使用utf8编码读取，避免中文乱码
        case_sensitive=False,          # 读取环境变量时忽略大小写，写大写/小写都能识别
    )

    # ── 数据库 ──
    # 异步PostgreSQL数据库连接地址，账号密码库名全部写在这里
    DATABASE_URL: str = "postgresql+asyncpg://review:review@localhost:5432/reviewanalyzer"

    # ── Redis / Celery 异步任务队列 ──
    # Celery消息中间件，任务存放在Redis的0号数据库
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    # Celery任务执行结果存储地址，同样使用Redis 0库
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ── MinIO 对象存储（存CSV、报告文件） ──
    # MinIO服务地址：本机9000端口
    MINIO_ENDPOINT: str = "localhost:9000"
    # MinIO登录账号
    MINIO_ACCESS_KEY: str = "minioadmin"
    # MinIO登录密码
    MINIO_SECRET_KEY: str = "minioadmin"
    # 存放项目文件的存储桶名称
    MINIO_BUCKET: str = "review-analyzer"
    # 是否开启HTTPS连接，本地开发关闭=False
    MINIO_SECURE: bool = False

    # ── AI 引擎 相关参数 ──
    # 使用的AI模型引擎，可选 claude / opencode / none
    CLI_ENGINE: str = "claude"
    # 单次调用AI工具的最大超时时间，单位秒
    CLI_TIMEOUT: int = 600
    # 同时运行的AI分析任务最大并发数量，防止服务器资源打满
    MAX_CONCURRENT_AGENTS: int = 4

    # ── 应用基础配置 ──
    # 运行环境：development开发环境 / production线上生产环境
    APP_ENV: str = "development"
    # 日志打印等级，info只会打印常规日志，debug会输出全部详细日志
    LOG_LEVEL: str = "info"
    # 允许跨域访问后端的前端网页地址列表
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

# 实例化配置对象，项目全局统一导入这个settings读取所有配置
settings = Settings()