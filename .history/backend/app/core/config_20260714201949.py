"""
全局配置管理 — 基于 pydantic-settings，从 .env 和环境变量读取所有配置项
"""
from pydantic_settings import BaseSettings, SettingsConfigDict # 导入配置基础类与配置规则类

class Settings(BaseSettings): # 定义项目全局配置类，统一存放所有参数
    """ReviewAnalyzer 全局配置"""

    model_config = SettingsConfigDict( # 配置环境变量读取规则
        env_file=".env", # 指定读取项目根目录下的.env配置文件
        env_file_encoding="utf-8", # 设置.env文件编码为utf-8，防止中文乱码
        case_sensitive=False, # 读取环境变量不区分大小写，兼容多种写法
    )

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://review:review@localhost:5432/reviewanalyzer" # 异步PostgreSQL数据库完整连接地址，包含账号密码库名

    # ── Redis / Celery 异步任务队列 ──
    CELERY_BROKER_URL: str = "redis://localhost:6379/0" # Celery消息中间件地址，任务队列存放于Redis 0号库
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0" # Celery任务运行结果存储地址，复用Redis 0号库

    # ── MinIO 对象存储（存CSV、报告文件） ──
    MINIO_ENDPOINT: str = "localhost:9000" # MinIO文件存储服务本地访问地址与端口
    MINIO_ACCESS_KEY: str = "minioadmin" # MinIO登录用户名
    MINIO_SECRET_KEY: str = "minioadmin" # MinIO登录密码
    MINIO_BUCKET: str = "review-analyzer" # 项目专属文件存储桶名称
    MINIO_SECURE: bool = False # 是否启用HTTPS连接MinIO，本地开发关闭

    # ── AI 引擎 相关参数 ──
    CLI_ENGINE: str = "claude" # 选用的AI分析引擎，可选claude、opencode、none
    CLI_TIMEOUT: int = 600 # 单次调用AI工具的超时限制，单位秒
    MAX_CONCURRENT_AGENTS: int = 4 # 允许同时运行的AI分析任务最大并发数，限制服务器负载

    # ── 应用基础配置 ──
    APP_ENV: str = "development" # 项目运行环境，development开发环境 / production线上环境
    LOG_LEVEL: str = "info" # 日志输出等级，debug打印全量日志，info仅打印关键运行日志
    CORS_ORIGINS: list[str] = ["http://localhost:3000"] # 允许跨域请求的前端网页地址列表

settings = Settings() # 实例化全局配置对象，项目任意文件导入读取配置