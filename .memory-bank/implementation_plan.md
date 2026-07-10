# ReviewAnalyzer — 实施计划 (Implementation Plan)

> 版本: v2.0 | 日期: 2026-07-10 | 目标: 6-8 周 (1 人全职)
>
> 基于 [PRD.md](PRD.md) v2.0 和 [tech_stack.md](tech_stack.md) v2.0。
> 本计划定义从零到全栈可用的每一步具体操作和验证方式。
> **每个 Step 不包含代码**，只有清晰的做什么 + 怎么验证。

---

## 前置状态（已完成）

以下工作已在计划编写前完成，**不需要再执行**：

- ✅ `.memory-bank/` 旧文档已清理（architecture.md、implementation_plan_phase2.md、progress.md 已删除）
- ✅ `.memory-bank/PRD.md` v2.0 — 产品需求文档
- ✅ `.memory-bank/tech_stack.md` v2.0 — 技术选型文档
- ✅ `.memory-bank/implementation_plan.md` v2.0 — 本文件
- ⬜ `CLAUDE.md` 待创建 — 将在 Step 1 中完成
- ⬜ `.memory-bank/architecture.md` 待创建 — 将在 Step 1 中创建骨架，后续 Step 逐步填充
- ⬜ `.memory-bank/progress.md` 待创建 — 将在 Step 1 中完成

## 总体策略

```
构建顺序: 后端优先 → 前端跟进 → 工程化收尾
           Step 1-7 (后端核心) → Step 8-10 (前端) → Step 11-12 (Docker + 测试)
MVP 范围: 全 12 个 Step（Step 1-7 = 基础层, Step 8-12 = 增强层）
现有代码: review-analyzer-skill/ 保留不动, streamlit_app/ 待删除
Docker:    Step 11 最后引入，Step 1-10 用本地环境开发
```

### Step 依赖关系

```
Step 1: 项目骨架 + CLAUDE.md + architecture.md + progress.md
  │
  ├──▶ Step 2: 数据库模型 ──▶ Step 3: 文件存储(MinIO)
  │
  ├──▶ Step 4: 任务 CRUD API ──▶ Step 5: Celery + 分析Pipeline
  │                                      │
  └──────────────────────────────────────┼──▶ Step 6: SSE 实时进度
                                         │
                                         └──▶ Step 7: 报告 + 导出 API
                                                     │
                                                     ▼
                                             Step 8: 前端项目骨架
                                                     │
                                                     ▼
                                             Step 9: 前端页面 (6 路由)
                                                     │
                                                     ▼
                                             Step 10: 主题 + 看板组件
                                                     │
                                                     ▼
                                             Step 11: Docker Compose
                                                     │
                                                     ▼
                                             Step 12: 测试 + 文档
```

---

## Step 1: 项目骨架、CLAUDE.md 与开发环境

**目标**：清理残留代码，创建 `CLAUDE.md` 和 `progress.md`，建立 `backend/` 目录结构，安装依赖，确认可运行空白 FastAPI 应用。

### 1.1 清理残留 + 创建项目引导文件

**清理**：
- 删除 `streamlit_app/` 整个目录（如果存在）
- 确保 `review-analyzer-skill/` 整个目录不动

**创建 `CLAUDE.md`**（项目根目录）：
- 必须是 Always Rules 代码块格式（给 LLM 看的指令）
- 内容须包含以下规则（具体措辞和完整内容由实施时按照 PRD/tech_stack 生成）：
  - **文档驱动**：写代码前必须先读取 `.memory-bank/architecture.md`（含完整 DB schema）和 `.memory-bank/PRD.md`
  - **实施流程**：按 implementation_plan.md 的 Step 顺序执行 → 自动验证 → 用户手动确认 → 更新 progress.md → 下一步（禁止跳过/并行）
  - **模块化（最高优先级）**：每文件 ≤500 行；禁止 utils.py/helpers.py 万能杂物间；新建文件前先判断是否可归入现有模块
  - **代码质量**：Python ruff + mypy strict；TypeScript Biome + strict；Pydantic/Zod 校验；禁止硬编码敏感信息
  - 项目概述 + 技术栈速查 + 分析流水线约定 + 测试规范 + 常见陷阱
- 参考 `.memory-bank/PRD.md` 和 `.memory-bank/tech_stack.md` 中的技术选型，确保一致

**创建 `.memory-bank/progress.md`**：
- 包含与 implementation_plan.md 末尾进度表一致的 12 Step 跟踪表
- 初始状态：所有 Step = ⬜ 待开始
- 包含状态图例和完成率统计

### 1.3 创建 backend/ 目录骨架

按照 PRD §13 附录 A 的目录结构，创建以下空文件和目录：

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # pydantic-settings 配置
│   │   └── database.py            # AsyncSession + engine
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py              # 路由汇总
│   │   ├── deps.py                # 依赖注入
│   │   ├── tasks.py               # 任务 CRUD 端点
│   │   ├── reviews.py             # 评论数据端点
│   │   ├── reports.py             # 报告端点
│   │   ├── export.py              # 导出端点
│   │   └── upload.py              # 文件上传端点
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy declarative base
│   │   ├── task.py
│   │   ├── review.py
│   │   ├── persona.py
│   │   └── report.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── task.py
│   │   ├── review.py
│   │   ├── persona.py
│   │   └── report.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py
│   │   ├── pipeline_service.py
│   │   ├── storage_service.py
│   │   └── sse_manager.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── analysis_task.py
│   └── utils/
│       ├── __init__.py
│       └── asin_utils.py
├── alembic/
│   ├── env.py
│   └── versions/                  # 空目录
├── alembic.ini
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_tasks.py
│   ├── test_reviews.py
│   └── test_pipeline.py
├── requirements.txt
├── pyproject.toml
└── Dockerfile                     # 空文件占位，Step 11 再填充
```

### 1.4 编写最小 FastAPI 入口

在 `backend/app/main.py` 中：

- 创建 FastAPI 实例，设置 `title="ReviewAnalyzer API"`, `version="2.0.0"`
- 添加 CORS 中间件（允许 `localhost:3000`）
- 添加 `GET /api/health` 端点：
  - 返回 `{"status": "ok", "version": "2.0.0"}`
  - （后续 Step 会添加 `claude_cli_available` 字段）
- 注册 `api/router.py` 中的路由（当前 router.py 为空或只有 health 路由）
- 添加 FastAPI 生命周期事件（startup/shutdown），当前为空

### 1.5 配置管理

在 `backend/app/core/config.py` 中：

- 使用 `pydantic-settings` 的 `BaseSettings` 定义 `Settings` 类
- 包含字段：
  - `DATABASE_URL`: 默认 `postgresql+asyncpg://review:review@localhost:5432/reviewanalyzer`
  - `CELERY_BROKER_URL`: 默认 `redis://localhost:6379/0`
  - `CELERY_RESULT_BACKEND`: 默认 `redis://localhost:6379/0`
  - `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
  - `CLI_ENGINE`: 默认 `"claude"`
  - `MAX_CONCURRENT_AGENTS`: 默认 `4`
  - `APP_ENV`: 默认 `"development"`
  - `LOG_LEVEL`: 默认 `"info"`
- 配置 `.env` 文件读取（`model_config = SettingsConfigDict(env_file=".env")`）

### 1.6 依赖文件

在 `backend/requirements.txt` 中：

- 按照 tech_stack.md §7.1 的 Python 依赖清单填入所有依赖
- 先只取消注释 Web 框架 + 数据校验部分（fastapi, uvicorn, pydantic, pydantic-settings）
- 其余依赖暂时注释（后续 Step 逐步启用）

在 `backend/pyproject.toml` 中：

- 配置 ruff（`target-version = "py313"`, `line-length = 100`, `select = ["E","F","I","N","W","UP","B","C4","SIM"]`）
- 配置 mypy（`strict = true`, `python_version = "3.13"`）
- 配置 pytest（`asyncio_mode = "auto"`, `testpaths = ["tests"]`）

### 1.7 创建 .env 模板

在项目根目录创建 `.env.example`（按照 PRD §8.2 的环境变量清单），但所有服务地址默认指向 `localhost`（非 Docker 服务名）：

```bash
DATABASE_URL=postgresql+asyncpg://review:review@localhost:5432/reviewanalyzer
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=review-analyzer
CLI_ENGINE=claude
```

然后复制为 `.env`（加入 `.gitignore`）。

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `ls CLAUDE.md` | 文件存在，包含 Always Rules + 项目概述 + 编码规范 |
| 2 | `ls .memory-bank/progress.md` | 文件存在，12 Step 均标记为 ⬜ |
| 3 | `ls backend/app/main.py` | 文件存在 |
| 4 | `uv pip install -r backend/requirements.txt` | 无错误，fastapi/uvicorn/pydantic 已安装 |
| 5 | `ruff check backend/` | 无警告（空文件或仅 pass 的模块不会有 lint 错误） |
| 6 | `cd backend && uvicorn app.main:app --reload --port 8000` | 服务启动，无 crash |
| 7 | `curl http://localhost:8000/api/health` | 返回 `{"status":"ok","version":"2.0.0"}` |
| 8 | `curl http://localhost:8000/docs` | Swagger UI 可访问，显示 health 端点 |
| 9 | `.gitignore` 包含 `.env` | `git status` 不显示 `.env` 文件 |

---

## Step 2: 数据库模型与 Alembic 迁移

**目标**：PostgreSQL 中创建 7 张表，SQLAlchemy ORM 模型可正常 CRUD，Alembic 迁移脚本可执行。

### 2.1 启动本地 PostgreSQL 和 Redis

选择以下方式之一：

- **方式 A（推荐）**：用 Docker 单独启动 PG 和 Redis（不写 compose 文件，手动命令）：

  ```bash
  docker run -d --name review-pg \
    -e POSTGRES_USER=review -e POSTGRES_PASSWORD=review -e POSTGRES_DB=reviewanalyzer \
    -p 5432:5432 postgres:16-alpine

  docker run -d --name review-redis \
    -p 6379:6379 redis:7-alpine
  ```

- **方式 B**：本地直接安装 PostgreSQL 16 和 Redis 7

### 2.2 数据库引擎配置

在 `backend/app/core/database.py` 中：

- 从 `config.py` 的 `Settings` 读取 `DATABASE_URL`
- 创建 `create_async_engine` 实例，配置：
  - `pool_size=20`, `max_overflow=10`
  - `pool_pre_ping=True`（连接前检测有效性）
- 创建 `async_sessionmaker`，参数 `expire_on_commit=False`
- 实现 `get_db()` 异步生成器函数（依赖注入用）：
  - `yield session`
  - `try/except` 中 `commit` 或 `rollback`

### 2.3 SQLAlchemy 模型

严格按照 PRD §4.2 的 DDL 定义，创建以下模型文件：

**`backend/app/models/base.py`**：
- 定义 `Base = declarative_base()`
- 定义通用 mixin `TimestampMixin`（`created_at`, `updated_at`）
- 定义 `update_updated_at` 触发器函数（Python 层面用 SQLAlchemy 事件实现）

**`backend/app/models/task.py`** — `Task` 模型：
- 表名 `tasks`
- 字段严格对应 PRD §4.2 中 `tasks` 表的每列
- 包含 CHECK 约束：`status`（7 种状态）、`source`（csv/sorftime）、`site`（US/UK/DE/JP）、`progress`（0-100）
- `config` 字段类型为 `JSON`（SQLAlchemy `JSON` type）
- 建立与 `reviews`、`personas`、`analysis_reports` 的 `relationship`

**`backend/app/models/review.py`** — `Review` + `TaggedReview` 模型：
- `Review` 表名 `reviews`，字段对应 PRD §4.2 的 `reviews` 表
- `images` 字段类型为 `JSON`
- `TaggedReview` 表名 `tagged_reviews`，字段对应 PRD §4.2
- `tags` 字段类型为 `JSON`（22 维标签）
- 建立两者的 `relationship` 和外键

**`backend/app/models/persona.py`** — `Persona` + `GoldenSample` 模型：
- `Persona` 表名 `personas`，`tags` 为 `JSON`
- `GoldenSample` 表名 `golden_samples`
- 建立 `relationship` 和外键关联

**`backend/app/models/report.py`** — `AnalysisReport` 模型：
- 表名 `analysis_reports`
- `task_id` 设 `unique=True`（1 对 1 关系）
- `stats`、`strategic_json`、`chart_configs` 类型为 `JSON`
- `insights_md`、`html_content` 类型为 `Text`

**`backend/app/models/__init__.py`**：导入所有模型（Alembic 自动发现需要）。

### 2.4 Alembic 初始化

- 在 `backend/` 目录下执行 `alembic init alembic`
- 修改 `alembic/env.py`：
  - 设置 `target_metadata = Base.metadata`
  - 配置 `DATABASE_URL` 从 `app.core.config` 的 `Settings` 读取
- 修改 `alembic.ini`：
  - 把 `sqlalchemy.url` 设为占位值（实际通过 `env.py` 动态设置）
- 执行 `alembic revision --autogenerate -m "init: 7 tables"`
  - 自动生成的迁移脚本应包含所有 7 张表、索引、约束
- 检查生成的迁移脚本：确认包含 GIN 索引、CHECK 约束、`ON DELETE CASCADE`
- 执行 `alembic upgrade head`

### 2.5 编写数据库初始化脚本

在 `backend/app/core/` 中创建 `init_db.py`：

- 函数 `init_db()`：
  - 调用 `alembic upgrade head`
  - 打印初始化完成的表和索引信息

### 2.6 编写模型单元测试

在 `backend/tests/conftest.py` 中：

- 配置 `pytest-asyncio` fixture：创建测试用数据库引擎（使用 SQLite `aiosqlite` 或独立的 test PostgreSQL 数据库）
- fixture `db_session`：创建所有表 → 提供 session → 测试后 drop 所有表

在 `backend/tests/test_models.py`（新建）中：

- 测试 `Task` 创建：插入一条任务记录，读取验证所有字段
- 测试 `Task` CHECK 约束：`status="invalid"` 应抛出 `IntegrityError`
- 测试外键级联删除：创建 Task → 关联 Review → 删除 Task → Review 也被删除
- 测试 `TaggedReview` JSON 字段：写入 22 维标签 dict，读取后验证 key/value 正确
- 测试 `AnalysisReport` unique 约束：同一 task_id 插两条应报错

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `docker ps` 查看 postgres 和 redis 容器 | 两个容器 `Up` 状态 |
| 2 | `cd backend && alembic upgrade head` | 7 张表创建成功，无错误 |
| 3 | `psql -h localhost -U review -d reviewanalyzer -c "\dt"` | 列出 7 张表 |
| 4 | `psql ... -c "\d tasks"` | 显示 CHECK 约束、索引 |
| 5 | `psql ... -c "\d tagged_reviews"` | 显示 GIN 索引 |
| 6 | `pytest backend/tests/test_models.py -v` | 所有测试通过 |
| 7 | `ruff check backend/app/models/` | 无警告 |
| 8 | `mypy backend/app/models/ --strict` | 无类型错误 |

---

## Step 3: 文件上传与 MinIO 集成

**目标**：CSV 文件可上传至 MinIO，数据库记录上传元数据，存储服务可读可删。

### 3.1 启动 MinIO

```bash
docker run -d --name review-minio \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 9000:9000 -p 9001:9001 \
  minio/minio:latest server /data --console-address ":9001"
```

### 3.2 创建 uploads 模型

在 `backend/app/models/` 中创建 `upload.py` — `Upload` 模型：
- 表名 `uploads`
- 字段按照 PRD §4.2 的 `uploads` 表定义：`id`, `original_name`, `stored_path`, `size_bytes`, `review_count`, `storage_backend`, `created_at`
- 添加到 `__init__.py` 的 import

### 3.3 生成 Alembic 迁移

- `alembic revision --autogenerate -m "add uploads table"`
- 检查迁移脚本，确认 `uploads` 表 DDL 正确
- `alembic upgrade head`

### 3.4 实现 MinIO 存储服务

在 `backend/app/services/storage_service.py` 中：

- 实现 `StorageService` 类：
  - `__init__`：从 config 获取 MinIO 连接参数，创建 MinIO client
  - `ensure_bucket()`：检查 bucket 是否存在，不存在则创建；在 FastAPI startup 事件中调用
  - `upload_csv(file_content: bytes, original_name: str) -> str`：上传文件到 MinIO，返回 object key
  - `get_file(object_key: str) -> bytes`：下载文件内容
  - `delete_file(object_key: str)`：删除文件
  - `get_presigned_url(object_key: str, expires: int = 3600) -> str`：获取临时下载链接

### 3.5 实现文件上传 API

在 `backend/app/api/upload.py` 中：

- `POST /api/upload/csv`：
  - 接收 `UploadFile`（FastAPI 内置）
  - 校验：仅 `.csv` 扩展名、文件大小 ≤ 50MB
  - 调用 `storage_service.upload_csv()` 上传到 MinIO
  - 使用 `data_loader.load_reviews_from_file()` 解析 CSV（将文件内容先临时写入磁盘或直接从 bytes 读取），获取评论条数
  - 写入 `uploads` 表记录
  - 返回 `201` + upload_id、文件名、大小、评论条数、前 10 行预览数据

- `GET /api/upload/history`：
  - 查询 `uploads` 表，按 `created_at DESC` 排序
  - 支持 `?limit=20` 分页
  - 返回上传记录列表

### 3.6 编写测试

在 `backend/tests/test_upload.py`（新建）中：

- 准备一个有效的小 CSV 文件作为测试 fixture（包含 5-10 行评论数据）
- 测试：上传有效 CSV → 返回 201 + preview 数据
- 测试：上传非 CSV 文件（如 .txt）→ 返回 400
- 测试：上传超过 50MB 的文件 → 返回 413 或 400
- 测试：`GET /api/upload/history` → 返回列表
- 测试：MinIO 中文件存在（用 `storage_service.get_file()` 验证）

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `curl http://localhost:9001` (MinIO Console) | MinIO Web 界面可访问 |
| 2 | `curl -X POST http://localhost:8000/api/upload/csv -F "file=@test.csv"` | 返回 201 + preview |
| 3 | MinIO Console 中查看 bucket | test.csv 已存储 |
| 4 | 上传非 CSV 文件 | 返回 400 + 中文错误提示 |
| 5 | `curl http://localhost:8000/api/upload/history` | 返回刚上传的记录 |
| 6 | `pytest backend/tests/test_upload.py -v` | 所有测试通过 |
| 7 | `ruff check backend/app/services/ backend/app/api/upload.py` | 无警告 |

---

## Step 4: 任务 CRUD API

**目标**：完整实现任务的创建、列表查询、详情查询、删除、重试 API。不含分析执行逻辑（Step 5 加入）。

### 4.1 实现 Pydantic Schema

在 `backend/app/schemas/task.py` 中：

- `TaskConfig`：`max_reviews`（500, ge=10, le=2000）, `batch_size`（20, ge=5, le=50）, `template`（"premium-gold"）
- `TaskCreate`：`asin`（含 `@field_validator` 校验 10 位大写字母数字）, `site`（Literal["US","UK","DE","JP"]，默认 "US"）, `source`（"csv"|"sorftime"，默认 "csv"）, `upload_id`（Optional[UUID]，source=csv 时必填）, `config`（TaskConfig，默认值）
- `TaskResponse`：所有 `tasks` 表字段映射，`model_config = {"from_attributes": True}`
- `TaskListResponse`：`tasks: list[TaskResponse]`, `total: int`
- `TaskStatus`：Literal["pending","fetching","tagging","analyzing","rendering","done","failed"]

### 4.2 实现 TaskService

在 `backend/app/services/task_service.py` 中：

- 实现 `TaskService` 类（依赖注入 `get_db` 的 session）：
  - `create_task(data: TaskCreate) -> TaskResponse`：
    - 校验：`source="csv"` 时 `upload_id` 不为空，且 upload_id 对应的上传记录存在
    - 创建 Task 记录（status="pending", progress=0）
    - 返回创建的任务
  - `get_task(task_id: UUID) -> TaskResponse`：
    - 查询任务，不存在则抛 HTTPException(404)
  - `list_tasks(status: Optional[str], offset: int, limit: int) -> TaskListResponse`：
    - 按 `created_at DESC` 排序
    - 支持按 status 筛选
    - 返回 `tasks` + `total` 计数
  - `delete_task(task_id: UUID)`：
    - 软策略：不允许删除 "running" 状态的任务（返回 409）
    - 删除任务（CASCADE 自动清理关联数据）
    - 返回 204
  - `retry_task(task_id: UUID) -> TaskResponse`：
    - 仅 "failed" 状态可重试 → 重置为 "pending", progress=0
    - 其他状态返回 409

### 4.3 实现 Task API 路由

在 `backend/app/api/tasks.py` 中：

- `POST /api/tasks` → 调用 `task_service.create_task()`
- `GET /api/tasks` → 调用 `task_service.list_tasks()`，query 参数 `status`, `offset`, `limit`
- `GET /api/tasks/{task_id}` → 调用 `task_service.get_task()`
- `DELETE /api/tasks/{task_id}` → 调用 `task_service.delete_task()`
- `POST /api/tasks/{task_id}/retry` → 调用 `task_service.retry_task()`

在 `backend/app/api/router.py` 中：
- 汇总所有路由：`api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])`

### 4.4 注册路由到 main.py

- 在 `backend/app/main.py` 中 `app.include_router(api_router, prefix="/api")`

### 4.5 编写测试

在 `backend/tests/test_tasks.py`（新建）中：

- **创建任务测试**：
  - 先上传一个 CSV，拿到 upload_id
  - POST `/api/tasks` → 返回 201 + TaskResponse 所有字段非空
  - POST `/api/tasks` 传入非法 ASIN → 返回 422（Pydantic 自动校验）
  - POST `/api/tasks` source=csv 但不传 upload_id → 返回 422 或自定义 400
- **列表查询测试**：
  - 创建 3 个不同 status 的任务
  - GET `/api/tasks` → 返回 3 条，`total=3`
  - GET `/api/tasks?status=done` → 筛选生效
  - GET `/api/tasks?offset=1&limit=1` → 分页生效
- **详情查询测试**：
  - GET `/api/tasks/{id}` → 返回正确任务
  - GET `/api/tasks/{不存在的 id}` → 404
- **删除测试**：
  - DELETE `/api/tasks/{id}` → 204
  - 再次 GET → 404
- **重试测试**：
  - 手动把任务 status 改为 "failed"
  - POST `/api/tasks/{id}/retry` → status 变为 "pending", progress=0

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `curl -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" -d '{...}'` | 返回 201 + 任务数据 |
| 2 | `curl http://localhost:8000/api/tasks` | 返回 JSON 列表 |
| 3 | `curl http://localhost:8000/api/tasks/{id}` | 返回单条任务详情 |
| 4 | `curl -X DELETE http://localhost:8000/api/tasks/{id}` | 返回 204 |
| 5 | `curl http://localhost:8000/docs` → 展开 POST /api/tasks | Swagger 显示 schema + 可 Try it out |
| 6 | `pytest backend/tests/test_tasks.py -v` | 所有测试通过 |
| 7 | `ruff check backend/app/schemas/ backend/app/services/ backend/app/api/` | 无警告 |
| 8 | `mypy backend/app/schemas/ backend/app/services/ --strict` | 无类型错误 |

---

## Step 5: Celery 任务 + 分析 Pipeline 集成

**目标**：创建分析任务后自动触发 Celery 异步执行 5 Phase 分析，分析结果写入数据库。

### 5.1 Celery 应用初始化

在 `backend/app/tasks/celery_app.py` 中：

- 创建 Celery 实例，broker 和 backend 从 config 读取
- 配置项严格按照 tech_stack.md §2.4 的 Celery 配置：
  - `task_serializer="json"`, `result_serializer="json"`
  - `task_acks_late=True`
  - `task_reject_on_worker_lost=True`
  - `task_soft_time_limit=900`（15 分钟）
  - `task_time_limit=1200`（20 分钟）
  - `worker_prefetch_multiplier=1`
  - `task_default_retry_delay=60`
  - `task_max_retries=3`
- 添加 `task_prerun` 信号处理：更新 Task 状态为当前 Phase
- 添加 `task_failure` 信号处理：更新 Task 状态为 "failed"，写入 `error_message`

### 5.2 分析任务定义

在 `backend/app/tasks/analysis_task.py` 中：

- 定义 Celery task `run_analysis_pipeline(task_id: str, config: dict)`：
  - 参数：`task_id`（UUID 字符串）、`config`（max_reviews, batch_size, template, upload_id 等）
  - 流程严格按照 PRD §7.1 的数据流图执行：
    1. **Phase 1: 数据获取**
       - 从 `uploads` 表获取 CSV 文件路径
       - 调用 `load_reviews_from_file()` 加载评论
       - 写入 `reviews` 表（批量 insert）
       - 更新 task 状态（status="tagging", progress=20, current_phase=2）
       - 调用 `sse_manager.broadcast(phase=1, ...)`
    2. **Phase 2: AI 打标**
       - 调用 `analyze_all(reviews, batch_size=config["batch_size"])`
       - 将打标结果写入 `tagged_reviews` 表（批量 insert）
       - 更新 task（status="analyzing", progress=40, current_phase=3）
       - 调用 `sse_manager.broadcast(phase=2, ...)`
    3. **Phase 3: 用户画像**
       - 调用 `analyze_user_personas(tagged_reviews)`
       - 将画像和黄金样本写入 `personas` 和 `golden_samples` 表
       - 更新 task（status="rendering", progress=60, current_phase=4）
       - 调用 `sse_manager.broadcast(phase=3, ...)`
    4. **Phase 4: 洞察报告**
       - 调用 `calculate_stats_summary()` + `generate_insights()`
       - 将 MD 报告写入 `analysis_reports` 表
       - 更新 task（progress=80, current_phase=5）
       - 调用 `sse_manager.broadcast(phase=4, ...)`
    5. **Phase 5: 输出看板**
       - 调用 `generate_outputs(analysis_data, output_config)`
       - 将 HTML 内容写入 `analysis_reports` 表
       - 上传 CSV/MD/HTML 文件到 MinIO
       - 更新 task（status="done", progress=100）
       - 调用 `sse_manager.broadcast(event="done", ...)`
  - 异常处理：
    - Phase 1 失败 → status="failed", error_phase=1, 提示数据获取失败
    - Phase 2 失败 → 重试 3 次，仍失败则 status="failed", error_phase=2
    - Phase 3-5 类似处理
    - 记录详细错误信息到 `error_message` 字段

### 5.3 实现 PipelineService

在 `backend/app/services/pipeline_service.py` 中：

- `PipelineService` 类：
  - `start_analysis(task_id: UUID, config: dict)`：调用 `run_analysis_pipeline.delay(task_id, config)`
  - 不直接执行分析，只负责触发 Celery 任务

### 5.4 集成到 Task 创建流程

修改 `backend/app/services/task_service.py` 的 `create_task()`：

- 创建 Task 记录后，调用 `pipeline_service.start_analysis(task_id, task.config)`
- 立即返回 TaskResponse（status="pending"，不会阻塞 HTTP 响应）

### 5.5 处理 review-analyzer-skill 路径

确保 `backend/` 能 import `review-analyzer-skill/` 的模块：

- 在 `backend/app/` 的入口处添加 `sys.path` 设置，将 `review-analyzer-skill/` 加入模块搜索路径
- 或使用相对路径：`from review_analyzer_skill.src.review_analyzer import analyze_all`
- 选择最简单不侵入现有代码的方式

### 5.6 编写测试

在 `backend/tests/test_pipeline.py`（新建）中：

- Mock `subprocess.run()`（不使用真实 Claude CLI）
- 准备 fixture：有效 CSV 文件 + 上传记录 + 任务记录
- 测试：创建任务 → Celery task 同步执行（`apply()` 而非 `delay()`）→ 检查：
  - reviews 表中插入了正确数量的评论
  - tagged_reviews 表中插入了打标结果
  - personas 表中有画像数据
  - analysis_reports 表中有报告
  - task.status = "done", progress = 100
- 测试：Phase 2 失败 → task.status = "failed", error_phase = 2, 有 error_message
- 测试：缺少 `claude` CLI → task.status = "failed"，提示安装 Claude Code CLI

在 `backend/tests/conftest.py` 中：
- 添加 `celery_session_app` 和 `celery_session_worker` fixture（测试用 Celery）
- 或使用 `CELERY_TASK_ALWAYS_EAGER = True`（同步执行，简单且适合单元测试）

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | 启动 Celery worker: `cd backend && celery -A app.tasks.celery_app worker --loglevel=info` | worker 启动，显示连接 Redis，等待任务 |
| 2 | 创建分析任务 (POST /api/tasks) | 返回 201，worker 日志显示 "Task run_analysis_pipeline received" |
| 3 | 查看 worker 日志 | 显示 5 Phase 执行日志 |
| 4 | `curl http://localhost:8000/api/tasks/{id}` | status 从 pending → fetching → ... → done，progress 逐步增加 |
| 5 | `psql ... -c "SELECT count(*) FROM reviews WHERE task_id='...'"` | 评论条数与 CSV 一致 |
| 6 | `psql ... -c "SELECT count(*) FROM tagged_reviews WHERE task_id='...'"` | 打标条数与评论条数一致 |
| 7 | `psql ... -c "SELECT count(*) FROM personas WHERE task_id='...'"` | 画像数 > 0 |
| 8 | `psql ... -c "SELECT insights_md FROM analysis_reports WHERE task_id='...'"` | Markdown 内容非空 |
| 9 | `pytest backend/tests/test_pipeline.py -v` | 所有测试通过（含 mock） |
| 10 | `ruff check backend/app/tasks/ backend/app/services/pipeline_service.py` | 无警告 |

---

## Step 6: SSE 实时进度推送

**目标**：前端可通过 EventSource 监听分析进度，Phase 切换时实时收到事件。

### 6.1 实现 SSEManager

在 `backend/app/services/sse_manager.py` 中：

- 实现 `SSEManager` 类（单例）：
  - `_connections: Dict[UUID, set[asyncio.Queue]]`：task_id → 一组等待事件流的队列
  - `async subscribe(task_id: UUID) -> asyncio.Queue`：
    - 为该 task 创建一个新队列
    - 加入 `_connections[task_id]`
    - 返回队列供 SSE 端点使用
  - `unsubscribe(task_id: UUID, queue: asyncio.Queue)`：
    - 从 `_connections[task_id]` 中移除队列
    - 如果该 task 的连接集合为空，删除整个 key
  - `async broadcast(task_id: UUID, event: str, data: dict)`：
    - 遍历 `_connections[task_id]` 中的所有队列
    - 向每个队列 `put` 格式化的 SSE 消息（`f"event: {event}\\ndata: {json.dumps(data)}\\n\\n"`）
    - 如果某个队列已满（消费者已断开），跳过

### 6.2 实现 SSE 端点

在 `backend/app/api/tasks.py` 中添加：

- `GET /api/tasks/{task_id}/stream`：
  - 设置为 `response_class=StreamingResponse`，`media_type="text/event-stream"`
  - 设置响应头：`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`（禁用 nginx 缓冲）
  - 从 `sse_manager.subscribe(task_id)` 获取队列
  - 循环 `async for event_data in queue`：
    - `yield event_data`
  - 断开时调用 `sse_manager.unsubscribe(task_id, queue)`
  - 如果任务已经完成（done/failed），直接发送一个 `done` 或 `error` 事件然后关闭连接

### 6.3 集成到 Celery 任务

修改 `backend/app/tasks/analysis_task.py`：

- 在每个 Phase 开始/完成时调用 `sse_manager.broadcast()`
- 广播的 data 格式严格按照 PRD §5.2.6 的 SSE 事件规范：
  - `event: "progress"`, `data: {"phase": N, "phase_name": "...", "message": "...", "progress": P}`
  - `event: "done"`, `data: {"task_id": "...", "status": "done", "total_reviews": N}`
  - `event: "error"`, `data: {"phase": N, "message": "..."}`

注意：Celery worker 运行在独立进程中，`sse_manager` 单例需要在不同进程间共享。解决方案：
- 使用 Redis Pub/Sub 作为中间层：
  - Celery 任务 `publish` 进度事件到 Redis channel
  - FastAPI 进程中 `subscribe` 该 channel，收到消息后调用 `sse_manager.broadcast()`
- 或在 FastAPI 启动时启动一个后台任务监听 Redis channel

### 6.4 编写测试

在 `backend/tests/test_sse.py`（新建）中：

- 测试：订阅一个 task → broadcast 消息 → 队列收到正确格式的消息
- 测试：多个连接订阅同一 task → broadcast → 所有连接都收到
- 测试：连接断开后 unsubscribe → 该任务连接数正确减少
- 测试：`GET /api/tasks/{id}/stream` → Content-Type 为 `text/event-stream`
- 测试：已完成任务请求 SSE → 直接返回 done 事件后关闭

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | 用 curl 连接 SSE: `curl -N http://localhost:8000/api/tasks/{id}/stream` | 持续输出 SSE 事件 |
| 2 | 创建分析任务 | curl 连接中逐步收到 phase 1→5 的 progress 事件 |
| 3 | 分析完成后 | 收到 `event: done` 事件，连接关闭 |
| 4 | 模拟失败 | 收到 `event: error` 事件，包含错误信息 |
| 5 | 打开 3 个终端同时 curl 同一 SSE | 3 个都收到相同事件 |
| 6 | `pytest backend/tests/test_sse.py -v` | 所有测试通过 |
| 7 | `ruff check backend/app/services/sse_manager.py` | 无警告 |

---

## Step 7: 报告查询与导出 API

**目标**：前端可查询分析报告数据（JSON 格式），可下载 CSV/MD/HTML 文件。

### 7.1 实现报告查询 API

在 `backend/app/api/reports.py` 中：

- `GET /api/tasks/{task_id}/report`：
  - 查询 `analysis_reports` 表
  - 返回 `ReportResponse` schema：
    - `insights_md`（全文）
    - `stats`（JSON 统计数据）
    - `chart_configs`（JSON 图表配置，供前端 Chart.js 直接消费）
    - `html_content`（全文 HTML 看板）
    - `template_name`
    - `generated_at`
  - 任务未完成时返回 404 + "报告尚未生成，当前状态: {status}"
  - 任务失败时返回 404 + "分析失败，无报告"

在 `backend/app/api/reviews.py` 中：

- `GET /api/tasks/{task_id}/reviews`：
  - 支持分页 `?offset=0&limit=50`
  - 支持评分筛选 `?rating_min=3&rating_max=5`
  - 返回 `ReviewListResponse`：`reviews: list[ReviewResponse]`, `total: int`

- `GET /api/tasks/{task_id}/tagged`：
  - 支持标签筛选 `?tag_key=人群_性别&tag_value=女性`
  - 支持分页
  - 返回 tagged reviews 列表

- `GET /api/tasks/{task_id}/personas`：
  - 返回所有画像 + 每个画像的黄金样本（JOIN golden_samples）
  - 结构按照 PRD §5.2.4 定义

### 7.2 实现导出 API

在 `backend/app/api/export.py` 中：

- `GET /api/tasks/{task_id}/export/csv`：
  - 从 MinIO 获取打标 CSV 文件
  - 设置 `Content-Type: text/csv; charset=utf-8`
  - 设置 `Content-Disposition: attachment; filename="{ASIN}_打标数据.csv"`
  - 返回 `StreamingResponse`（大文件流式传输）

- `GET /api/tasks/{task_id}/export/md`：
  - 从 `analysis_reports.insights_md` 获取内容
  - `Content-Type: text/markdown; charset=utf-8`
  - 文件名 `{ASIN}_洞察报告.md`

- `GET /api/tasks/{task_id}/export/html`：
  - 从 MinIO 获取 HTML 看板文件
  - `Content-Type: text/html; charset=utf-8`
  - 文件名 `{ASIN}_看板.html`

### 7.3 注册路由

更新 `backend/app/api/router.py`：

- `api_router.include_router(reports.router, prefix="/tasks", tags=["reports"])`
- `api_router.include_router(reviews.router, prefix="/tasks", tags=["reviews"])`
- `api_router.include_router(export.router, prefix="/tasks", tags=["export"])`

### 7.4 编写测试

在 `backend/tests/test_reports.py`（新建）中：

- 创建一个已完成的分析任务（mock 数据写入 reports 表）
- 测试 `GET /api/tasks/{id}/report` → 返回完整 JSON，包含 insights_md, stats, chart_configs
- 测试未完成任务 → 404
- 测试 `GET /api/tasks/{id}/reviews` → 分页正确
- 测试 `GET /api/tasks/{id}/reviews?rating_min=4` → 筛选生效
- 测试 `GET /api/tasks/{id}/tagged?tag_key=人群_性别&tag_value=女性` → 标签筛选生效
- 测试 `GET /api/tasks/{id}/personas` → 返回画像列表 + 黄金样本

在 `backend/tests/test_export.py`（新建）中：

- 测试 `GET /api/tasks/{id}/export/csv` → Content-Type 正确 + 响应体是 CSV 格式
- 测试 `GET /api/tasks/{id}/export/md` → 文件名正确
- 测试未完成任务的导出 → 404

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `curl http://localhost:8000/api/tasks/{id}/report` | 返回完整 JSON（insights_md, stats...） |
| 2 | `curl http://localhost:8000/api/tasks/{id}/reviews?offset=0&limit=10` | 返回 10 条评论 + total 计数 |
| 3 | `curl "http://localhost:8000/api/tasks/{id}/tagged?tag_key=人群_性别&tag_value=男性"` | 仅返回匹配的 tagged reviews |
| 4 | `curl http://localhost:8000/api/tasks/{id}/personas` | 画像 + 黄金样本 |
| 5 | `curl -O http://localhost:8000/api/tasks/{id}/export/csv` | 下载的 CSV 可用 Excel 打开 |
| 6 | `curl -O http://localhost:8000/api/tasks/{id}/export/md` | 下载内容为完整 Markdown |
| 7 | `curl -O http://localhost:8000/api/tasks/{id}/export/html` | 浏览器打开 HTML，看板正常显示 |
| 8 | `pytest backend/tests/test_reports.py backend/tests/test_export.py -v` | 全部通过 |
| 9 | `ruff check backend/app/api/reports.py backend/app/api/reviews.py backend/app/api/export.py` | 无警告 |

---

## Step 8: 前端项目骨架与基础页面

**目标**：Next.js 项目初始化，shadcn/ui 集成，6 个路由页面骨架搭建，API client 封装。

### 8.1 初始化 Next.js 项目

```bash
cd /home/xing/ReviewAnalyzer
pnpm create next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
```

### 8.2 安装依赖

按照 tech_stack.md §7.2 安装所有依赖：

```bash
pnpm add zustand @tanstack/react-query chart.js react-chartjs-2
pnpm add react-markdown remark-gfm rehype-highlight mermaid
pnpm add react-hook-form @hookform/resolvers zod
pnpm add date-fns lucide-react
pnpm add -D vitest @testing-library/react @testing-library/jest-dom msw @playwright/test
pnpm add -D @biomejs/biome
```

### 8.3 配置 shadcn/ui

```bash
npx shadcn@latest init
# 选择: TypeScript, Neutral, CSS variables: Yes
```

安装需要的 shadcn 组件：
```bash
npx shadcn@latest add button card tabs progress badge separator dialog toast
npx shadcn@latest add input select textarea label form
npx shadcn@latest add table dropdown-menu sheet
```

### 8.4 配置代码质量工具

创建 `frontend/biome.json`（按照 tech_stack.md §3.7 的配置）：
- `indentStyle: space`, `indentWidth: 2`, `lineWidth: 100`
- `quoteStyle: double`, `semicolons: always`

更新 `frontend/tsconfig.json`：
- 确保 `strict: true`
- 添加路径别名 `@/* → ./src/*`

### 8.5 创建目录结构

```
frontend/src/
├── app/
│   ├── layout.tsx              # 根布局（Navbar + Container）
│   ├── page.tsx                # 首页 (Landing)
│   ├── tasks/
│   │   ├── page.tsx            # 任务仪表盘（主页面）
│   │   ├── new/
│   │   │   └── page.tsx        # 创建新任务
│   │   └── [id]/
│   │       ├── page.tsx        # 任务详情页
│   │       ├── report/
│   │       │   └── page.tsx    # 报告全屏
│   │       └── reviews/
│   │           └── page.tsx    # 评论数据浏览
│   └── export/
│       └── [id]/
│           └── page.tsx        # 导出下载页
├── components/
│   ├── ui/                     # shadcn/ui 组件（自动生成）
│   ├── layout/
│   │   ├── navbar.tsx          # 顶部导航栏
│   │   └── container.tsx       # 内容容器
│   ├── tasks/
│   │   ├── task-card.tsx       # 任务卡片
│   │   ├── task-list.tsx       # 任务列表
│   │   ├── create-form.tsx     # 创建表单
│   │   └── progress-bar.tsx    # 进度条
│   ├── dashboard/              # 看板组件（Step 10 填充）
│   └── themes/                 # 主题组件（Step 10 填充）
├── hooks/
│   ├── use-tasks.ts            # TanStack Query hooks
│   ├── use-sse.ts              # SSE 连接 hook
│   └── use-report.ts
├── stores/
│   ├── ui-store.ts             # UI 状态 (Zustand)
│   └── task-draft-store.ts     # 任务草稿 (Zustand)
├── lib/
│   ├── api-client.ts           # 封装 fetch / axios
│   ├── validators.ts           # Zod schemas
│   └── utils.ts
├── styles/
│   └── globals.css             # Tailwind + 主题变量
└── types/
    └── index.ts                # 共享 TypeScript 类型定义
```

### 8.6 实现 API Client

在 `frontend/src/lib/api-client.ts` 中：

- 创建 `ApiClient` 类或一组函数：
  - 基础 URL：`NEXT_PUBLIC_API_URL` 环境变量（默认 `http://localhost:8000/api`）
  - 通用 `request<T>(method, path, body?): Promise<T>` 函数
  - 自动 JSON 序列化/反序列化
  - 错误处理：非 2xx 响应抛出 `ApiError`（含 status + detail）
- 为每个 API 端点创建类型化的函数：
  - `uploadCSV(file: File): Promise<UploadResponse>`
  - `createTask(data: TaskCreate): Promise<TaskResponse>`
  - `listTasks(filters?): Promise<TaskListResponse>`
  - `getTask(id: string): Promise<TaskResponse>`
  - 等等...

### 8.7 实现 TypeScript 类型定义

在 `frontend/src/types/index.ts` 中：

- 定义所有与后端 Pydantic Schema 对齐的类型：
  - `TaskStatus`, `TaskConfig`, `TaskCreate`, `TaskResponse`, `TaskListResponse`
  - `ReviewResponse`, `TaggedReviewResponse`
  - `PersonaResponse`, `GoldenSampleResponse`
  - `ReportResponse`（含 `insights_md`, `stats`, `chart_configs`）

### 8.8 实现 Zod 校验 Schema

在 `frontend/src/lib/validators.ts` 中：

- `taskCreateSchema`：与后端 `TaskCreate` Pydantic 模型规则完全一致
- 导出 `TaskCreate = z.infer<typeof taskCreateSchema>`

### 8.9 搭建 Layout 和基础页面

**`app/layout.tsx`**：
- 导入 Navbar 组件
- 设置字体、全局 metadata（title="ReviewAnalyzer"）
- 包裹 `QueryClientProvider` + Zustand store

**`components/layout/navbar.tsx`**：
- Logo + 导航链接（首页 | 任务 | 关于）
- 主题选择器下拉（状态存 Zustand `currentTheme`）

**`app/page.tsx`（首页）**：
- Hero 区域：标题 "ReviewAnalyzer"，一句话描述，CTA 按钮 "开始分析"
- Feature 卡片区（3 列）：22维标签 / 14章报告 / 6套主题

**`app/tasks/page.tsx`（任务仪表盘）**：
- 左侧面板：任务列表（StatusFilter + TaskSearchInput + TaskCard 列表）
- 右侧面板：快速创建面板（AsinInput + SiteSelect + CsvUploader + ConfigForm + SubmitButton）
- 用 TanStack Query 的 `useQuery` 获取任务列表，条件轮询（有 running 任务时 5s 间隔）

**`app/tasks/[id]/page.tsx`（任务详情）**：
- 顶部：TaskHeader（ASIN + 状态徽章 + 时间）
- 运行中：ProgressSection（ProgressBar + PhaseIndicator）
- 已完成：ResultTabs（DashboardTab | ReportTab | ReviewsTab）— Tab 切换用 URL searchParams

### 8.10 实现 TanStack Query Hooks

在 `frontend/src/hooks/use-tasks.ts` 中：

- `useTasks(filters?)`：调用 `apiClient.listTasks()`
- `useTask(id)`：调用 `apiClient.getTask()`
- `useCreateTask()`：`useMutation`，成功后 invalidate `['tasks']`
- `useDeleteTask()`：`useMutation`，成功后 invalidate `['tasks']`

在 `frontend/src/hooks/use-report.ts` 中：

- `useReport(taskId)`
- `useReviews(taskId, filters)`
- `usePersonas(taskId)`

在 `frontend/src/hooks/use-sse.ts` 中：

- `useTaskProgress(taskId)`：
  - 创建 `EventSource` 连接到 `/api/tasks/{taskId}/stream`
  - `onmessage` → 解析事件 → 更新 React Query 缓存中的 task 数据
  - 收到 `done` / `error` 事件后关闭连接
  - `useEffect` cleanup 中关闭连接

### 8.11 编写前端测试

在 `frontend/tests/` 目录下：

- 使用 MSW 模拟后端 API 响应
- 测试首页渲染：检查 Hero 标题和 CTA 按钮存在
- 测试任务列表页面：MSW 返回 mock 任务列表 → 渲染正确数量的 TaskCard
- 测试 API client：`apiClient.createTask(mockData)` → 正确序列化和请求

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `cd frontend && pnpm dev` | Next.js 开发服务器在 localhost:3000 启动 |
| 2 | 浏览器打开 `http://localhost:3000` | 首页渲染，Hero 可见 |
| 3 | 浏览器打开 `http://localhost:3000/tasks` | 任务仪表盘页面渲染 |
| 4 | 上传 CSV + 输入 ASIN → 点击创建 | 调用后端 API（需后端运行） |
| 5 | `pnpm biome check src/` | 无 lint 错误 |
| 6 | `pnpm tsc --noEmit` | 无类型错误 |
| 7 | `pnpm vitest run` | 所有单元测试通过 |
| 8 | `pnpm build` | Next.js 生产构建成功，无错误 |

---

## Step 9: 前端页面全功能实现

**目标**：所有 6 个路由页面具备完整交互功能，与后端 API 全链路打通。

### 9.1 完善任务仪表盘 (`/tasks`)

- **TaskListPanel**：
  - StatusFilter：全部 / 运行中 / 已完成 / 失败，点击筛选触发 `useTasks({status})` 重新查询
  - TaskSearchInput：按 ASIN 模糊搜索（客户端过滤）
  - TaskCard：
    - 状态图标（pending=⏳, running=🔵, done=🟢, failed=🔴）
    - ASIN + 创建时间 + 进度条（仅 running）+ 评论条数 + 画像数
    - 点击跳转到 `/tasks/[id]`
    - 右侧 "删除" 按钮（二次确认 Dialog）

- **QuickCreatePanel**：
  - AsinInput：格式校验（10 位大写字母数字），实时反馈 ✓/✗
  - SiteSelect：下拉 US/UK/DE/JP
  - CsvUploader：拖拽或点击上传，上传中显示进度，完成后显示文件名 + 评论条数 + 前 10 行预览表格
  - ConfigForm：max_reviews 滑块（10-2000），template 下拉（6 套主题预览图）
  - SubmitButton：所有字段合法时启用，点击调用 `useCreateTask().mutate()`
  - 创建成功后 Toast 通知 + 自动跳转到 `/tasks/[id]`

### 9.2 完善任务详情页 (`/tasks/[id]`)

- **ProgressSection**（仅 running 状态）：
  - 使用 `useTaskProgress(taskId)` hook 监听 SSE
  - ProgressBar 动画 + 百分比数字
  - PhaseIndicator 列表（5 个 Phase 图标 + 名称），当前 Phase 高亮 + 动画
  - 当前 Phase 描述文字实时更新（"正在 AI 打标中... (47/100)"）
  - 完成时自动切换到 ResultTabs

- **ResultTabs**（仅 done 状态）：
  - Tab 切换状态存 URL searchParams (`?tab=dashboard`)
  - **DashboardTab**：嵌入 iframe 或直接渲染 HTML（`dangerouslySetInnerHTML`），全屏按钮、主题切换下拉
  - **ReportTab**：左侧悬浮 ReportNav（14 章锚点目录，点击滚动到对应章节），右侧 `react-markdown` 渲染 MD 内容，含 Mermaid 图表
  - **ReviewsTab**：
    - ReviewFilters：情感下拉（全部/积极/中性/消极）、评分范围滑块、标签维度下拉（人群_性别、使用_场景 等）
    - ReviewsTable：分页表格，列（review_id, body 截断, rating, sentiment, info_score, 日期）
    - 单行展开显示完整评论 + 全部 22 维标签

### 9.3 完善报告全屏页 (`/tasks/[id]/report`)

- 从后端加载 MD 内容
- 左侧 14 章 TOC 导航（固定悬浮，点击高亮当前章节）
- 右侧 Markdown 渲染区：
  - 使用 `react-markdown` + `remark-gfm` + `rehype-highlight`
  - Mermaid 代码块用 `mermaid.js` 客户端渲染为 SVG
  - 表格使用 shadcn/ui Table 样式覆盖

### 9.4 完善评论数据页 (`/tasks/[id]/reviews`)

- 顶部统计卡片行：总评论数、平均评分、积极/中性/消极计数
- 与 ReviewsTab 复用 ReviewFilters + ReviewsTable 组件
- URL 参数保持筛选状态（可分享的链接）

### 9.5 完善导出页 (`/export/[id]`)

- 三个下载卡片（CSV / Markdown / HTML），每张卡片：
  - 图标 + 格式名
  - 文件大小（从后端获取 Content-Length）
  - "下载" 按钮：点击触发浏览器文件下载
- 如果报告未生成，卡片灰显 + "报告未生成" 提示

### 9.6 实现 Zustand Stores

在 `frontend/src/stores/ui-store.ts` 中：
- `currentTheme: string` — 当前看板主题
- `sidebarOpen: boolean` — 侧边栏开关
- `toasts: Toast[]` — Toast 通知队列
- `addToast()`, `dismissToast()`

在 `frontend/src/stores/task-draft-store.ts` 中：
- 新建任务表单的所有字段临时存储（切换页面时不丢失）

### 9.7 编写测试

- 测试 `useSSE` hook：mock EventSource，验证收到 progress 事件后更新状态
- 测试创建任务流程：填写表单 → 点击提交 → API 被调用 → Toast 出现
- 测试评论筛选：选择情感=积极 → API 调用参数包含 `sentiment=积极`
- 测试导出按钮：点击导出 → API 被调用 → 触发浏览器下载

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `pnpm dev` + 后端运行 → 完整操作流程 | 上传 CSV → 创建任务 → 实时进度 → 看板展示 |
| 2 | 每个路由页面都可访问 | `/tasks`, `/tasks/[id]`, `/tasks/[id]/report`, `/tasks/[id]/reviews` |
| 3 | SSE 进度实时更新 | 进度条从 0% 走到 100%，Phase 描述更新 |
| 4 | 任务列表 5s 轮询 | 未完成任务的卡片进度条自动更新 |
| 5 | 历史任务可查看 | 点击已完成任务 → 切换到结果 Tab |
| 6 | 切换 Tab 时 URL 更新 | `?tab=dashboard` → `?tab=report` |
| 7 | `pnpm biome check src/` | 无 lint 错误 |
| 8 | `pnpm tsc --noEmit` | 无类型错误 |
| 9 | `pnpm vitest run` | 所有测试通过 |
| 10 | `pnpm build` | 生产构建成功 |

---

## Step 10: 6 套主题与看板可视化组件

**目标**：React 组件重写 6 套主题的 Dashboard 可视化模块，复用后端返回的 Chart.js 配置。

### 10.1 提炼 CSS 设计 Token

从 `review-analyzer-skill/src/templates/` 的 6 套主题 CSS 中提取变量：

- 在 `frontend/src/styles/globals.css` 中定义：
  - `:root` — 默认主题（premium-gold）的 CSS 变量
  - `[data-theme="dark-tech"]`、`[data-theme="linear-minimal"]` 等 — 其他 5 套
  - 约 30 个 CSS token（颜色、字体、圆角、阴影、毛玻璃参数）

### 10.2 创建 ThemeProvider

在 `frontend/src/components/themes/theme-provider.tsx` 中：

- 从 Zustand `currentTheme` 读取当前主题
- 在 `<html>` 元素上设置 `data-theme` 属性
- 读取对应的 CSS 变量配置
- 提供 `ThemeContext` 给子组件

### 10.3 创建看板核心组件

在 `frontend/src/components/dashboard/` 目录下创建：

**`stat-cards.tsx`** — 指标卡片行：
- 4 个卡片：总评论数 | 平均评分 | 情感积极率 | 画像数
- 每张卡片：大数字 + 标签 + 环比变化箭头（如果有）
- 样式：毛玻璃背景 + 边框 + 主题色

**`pie-chart.tsx`** — 情感分布饼图：
- 接收后端 `chart_configs.sentiment_pie` 配置
- 使用 `react-chartjs-2` 的 `<Pie>` 组件
- 居中图例 + 百分比标签

**`radar-chart.tsx`** — 22 维标签雷达图：
- 接收后端 `chart_configs.tags_radar` 配置
- 多维度在一个雷达图上展示
- 响应式大小

**`bar-chart.tsx`** — TOP 标签柱状图：
- 接收后端 `chart_configs.top_tags_bar` 配置
- 横向柱状图，TOP 10-15 标签
- 不同颜色区分维度类别

**`line-chart.tsx`** — 月度评分趋势：
- 接收 `chart_configs.rating_trend` 配置
- X 轴 = 月份，Y 轴 = 平均评分

**`persona-card.tsx`** — 画像卡片：
- 画像名 + 人数 + 颜色标识
- 特征标签（Tag 组件，不同颜色）
- 黄金样本引用（blockquote 样式，正面绿色、负面红色）
- 一句话总结

**`tag-cloud.tsx`** — 标签词云（可选，P1）：
- 基于 TOP 标签的频率渲染不同大小的标签

### 10.4 组装 DashboardView

创建 `frontend/src/components/dashboard/dashboard-view.tsx`：

- 接收 `ReportResponse` 数据
- 从上到下排列：StatCards → PieChart + RadarChart (2列) → BarChart → PersonaCards (2x2 grid) → LineChart
- 所有图表共享主题的 `chart-colors` 变量
- 使用 Tailwind 的 responsive grid

### 10.5 创建 6 套主题定义文件

在 `frontend/src/components/themes/` 下为每套主题创建定义文件：

```
themes/
├── theme-provider.tsx
├── types.ts                     # ThemeDefinition 类型
├── premium-gold.ts
├── dark-tech.ts
├── linear-minimal.ts
├── posthog-analytics.ts
├── stripe-executive.ts
└── warm-editorial.ts
```

每个文件导出 `ThemeDefinition` 对象（tokens + 元数据）。

### 10.6 编写测试

- 测试 ThemeProvider：切换主题 → `<html>` 的 `data-theme` 属性正确变化
- 测试 StatCards：传入 mock 数据 → 卡片显示正确数值
- 测试 PieChart：传入 chart_configs → Chart.js 实例创建（检查 canvas 渲染）
- 测试 PersonaCard：传入 mock 画像数据 → 显示 name, count, tags, golden_samples
- 测试主题切换后图表颜色变化（snapshot 测试 CSS 变量）

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | 切换到 premium-gold 主题 | 看板显示黑金配色的玻璃拟态 UI |
| 2 | 切换到 dark-tech 主题 | 所有组件变为赛博朋克配色 |
| 3 | 6 个主题一一切换 | 每个主题配色与 Jinja2 原版视觉一致（肉眼对比） |
| 4 | StatCards 响应式布局 | 桌面 4 列、平板 2 列、手机 1 列 |
| 5 | PieChart 显示 | 饼图渲染，图例正确，hover 有 tooltip |
| 6 | PersonaCard 显示 | 画像卡片包含黄金样本引用 |
| 7 | `pnpm biome check src/components/` | 无 lint 错误 |
| 8 | `pnpm vitest run` | 全部测试通过 |
| 9 | `pnpm build` | 生产构建成功 |

---

## Step 11: Docker Compose 全栈部署

**目标**：一键 `docker compose up` 启动全部 7 个服务，浏览器访问完整应用。

### 11.1 编写 Backend Dockerfile

文件：`backend/Dockerfile`

- 基于 `python:3.13-slim`
- 安装系统依赖（`build-essential`, `libpq-dev` 等）
- 设置工作目录 `/app`
- 复制 `backend/` 和 `review-analyzer-skill/` 到容器
- 安装 Python 依赖：`uv pip install -r backend/requirements.txt`
- EXPOSE 8000
- CMD：`uvicorn app.main:app --host 0.0.0.0 --port 8000`

### 11.2 编写 Frontend Dockerfile

文件：`frontend/Dockerfile`

- 阶段 1（build）：基于 `node:22-alpine`
  - 复制 `frontend/` → `pnpm install --frozen-lockfile` → `pnpm build`
- 阶段 2（serve）：基于 `nginx:alpine`
  - 复制 build 产物到 nginx 静态目录
  - 复制 nginx 配置（SPA 路由 fallback）

### 11.3 编写 nginx.conf

文件：`nginx.conf`

- 反向代理配置：
  - `/` → frontend:3000（SPA 路由：try_files → index.html）
  - `/api/` → backend:8000
  - `/api/tasks/{id}/stream` → backend:8000（SSE，禁用缓冲：`proxy_buffering off`）

### 11.4 编写 docker-compose.yml

文件：`docker-compose.yml`

- 严格按照 PRD §8.1 的配置定义 7 个服务：
  - `nginx`（端口 80）
  - `frontend`（expose 3000）
  - `backend`（expose 8000，depends_on postgres + redis + minio）
  - `celery-worker`（同 backend image，不同 command）
  - `postgres`（端口 5432，healthcheck，volume）
  - `redis`（端口 6379，volume）
  - `minio`（端口 9000 + 9001，volume）
- 网络：`review-analyzer-net`（bridge）
- 卷：`pgdata`, `redisdata`, `miniodata`

### 11.5 编写 .env.example 更新

更新 `.env.example`，所有地址指向 Docker 服务名（而非 localhost）：

```bash
DATABASE_URL=postgresql+asyncpg://review:review@postgres:5432/reviewanalyzer
CELERY_BROKER_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
# ...
```

### 11.6 添加 Alembic 自动迁移到启动流程

在 `backend/app/core/init_db.py` 中添加：

- FastAPI startup 事件：`alembic upgrade head` 自动执行
- 可选：检查 MinIO bucket 是否存在，不存在则创建

### 11.7 编写 GitHub Actions CI（可选，加分项）

文件：`.github/workflows/ci.yml`

- 按照 tech_stack.md §5.2 的 CI Pipeline 定义：
  - backend-lint（ruff + mypy）
  - frontend-lint（biome + tsc --noEmit）
  - backend-test（pytest，含 PostgreSQL service container）
  - frontend-test（vitest）

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `docker compose build` | 4 个镜像构建成功（backend, frontend, celery-worker 复用 backend, nginx） |
| 2 | `docker compose up -d` | 7 个服务启动，无 crash-restart 循环 |
| 3 | `docker compose ps` | 所有服务 `Up` 或 `healthy` |
| 4 | `curl http://localhost/api/health` | 返回 `{"status":"ok","version":"2.0.0"}` |
| 5 | 浏览器 `http://localhost` | 首页渲染 |
| 6 | 浏览器 `http://localhost/api/docs` | Swagger UI 可访问 |
| 7 | 浏览器 `http://localhost:9001` | MinIO Console 可访问 |
| 8 | 上传 CSV → 创建任务 → 等待完成 → 查看报告 | 完整流程通过 |
| 9 | `docker compose down` → `docker compose up -d` | 数据持久化有效（历史任务还在） |

---

## Step 12: 测试完善与文档发布

**目标**：测试覆盖率达标（后端 ≥80%，前端 ≥80%），撰写 README，打 Git tag 发布。

### 12.1 后端测试补充

- 检查 `pytest --cov` 覆盖率报告
- 补充未覆盖的关键路径测试：
  - Celery 任务重试逻辑
  - SSE 连接异常断开
  - MinIO 上传失败 fallback
  - 并发创建任务
  - 大文件（接近 50MB）上传
- 目标：总体 ≥ 80%，`services/` 和 `tasks/` ≥ 85%

### 12.2 前端测试补充

- 检查 `vitest --coverage` 覆盖率报告
- 补充：
  - 各页面的加载状态（Skeleton）
  - 错误状态（API 500 → Error 页面）
  - 空状态（无任务时 → EmptyState 组件）
- 目标：≥ 80%

### 12.3 Playwright E2E 测试

在 `frontend/e2e/` 目录下（或在 `tests/e2e/` 中）：

- `task-flow.spec.ts`：完整用户流程
  1. 打开首页 → 点击"开始分析" → 导航到 `/tasks`
  2. 上传测试 CSV → 输入 ASIN → 点击提交
  3. 等待任务完成（mock 更快或等待真实完成）
  4. 验证看板渲染、Tab 切换、报告加载
- `history.spec.ts`：历史任务查看
- `export.spec.ts`：文件下载验证
- `theme-switch.spec.ts`：6 套主题切换

### 12.4 编写 README.md

在项目根目录重写 `README.md`：

- 顶部 Badge：MIT License / Docker / Build Status
- 一句话介绍 + 功能截图（或 GIF）
- 目录
- **快速开始**：
  ```bash
  git clone <repo>
  cd review-analyzer
  cp .env.example .env
  docker compose up -d
  # 打开 http://localhost
  ```
- **功能特性**：22维标签 / 14章报告 / 6套主题 / SSE 实时进度
- **技术栈**：链接到 `.memory-bank/tech_stack.md`
- **项目结构**：目录树
- **本地开发**：如何无 Docker 开发（后端 + 前端 + PG/Redis/MinIO）
- **API 文档**：链接到 `/api/docs`
- **贡献指南**：CLAUDE.md 规则链接
- **License**：MIT

### 12.5 创建 CHANGELOG.md

- v2.0.0 条目：列出所有 12 个 Step 的核心交付物
- 标注 breaking change：streamlit_app/ 移除

### 12.6 更新 .gitignore

确保以下被忽略：
- `.env`
- `.venv/`
- `__pycache__/`, `*.pyc`
- `node_modules/`
- `.next/`
- `output/`
- `backend/alembic/versions/*.pyc`
- `.coverage`, `coverage/`, `htmlcov/`

### 12.7 Git Tag + Release

```bash
git add -A
git commit -m "feat: ReviewAnalyzer v2.0 全栈版 — FastAPI + Next.js + PostgreSQL + Celery + MinIO"
git tag v2.0.0
git push origin main --tags
```

在 GitHub 上创建 Release：
- 标题：`v2.0.0 — 全栈产品化`
- 内容：从 CHANGELOG.md 粘贴
- 附件：无需（Docker 镜像通过 CI 推送到 GHCR）

### 验证方式

| # | 验证项 | 预期结果 |
|---|--------|---------|
| 1 | `pytest backend/ --cov --cov-report=term` | 覆盖率 ≥ 80% |
| 2 | `pnpm vitest run --coverage` | 覆盖率 ≥ 80% |
| 3 | `npx playwright test` | E2E 测试通过 |
| 4 | `ruff check backend/ && mypy backend/ --strict` | 无错误 |
| 5 | `pnpm biome check frontend/src/ && pnpm tsc --noEmit` | 无错误 |
| 6 | `docker compose up -d && curl http://localhost/api/health` | 返回 OK |
| 7 | 浏览器完整操作流程 | 上传 CSV → 分析 → 查看报告 → 下载文件 |
| 8 | README.md 在 GitHub 上格式正确 | 所有链接可点击，截图可见 |
| 9 | `git tag -l` | `v2.0.0` 存在 |

---

## 进度跟踪

| Step | 目标 | 状态 | 开始日期 | 完成日期 | 备注 |
|------|------|------|----------|----------|------|
| 1 | 项目骨架 + CLAUDE.md + progress.md | ⬜ | — | — | backend/ 目录 + FastAPI health + 引导文件 |
| 2 | 数据库 | ⬜ | — | — | 7 表 + Alembic |
| 3 | 文件存储 | ⬜ | — | — | MinIO + CSV 上传 |
| 4 | 任务 CRUD | ⬜ | — | — | 创建/列表/详情/删除/重试 |
| 5 | Pipeline | ⬜ | — | — | Celery + 5 Phase 分析 |
| 6 | SSE 进度 | ⬜ | — | — | 实时推送 + EventSource |
| 7 | 报告导出 | ⬜ | — | — | 查询 API + 文件下载 |
| 8 | 前端骨架 | ⬜ | — | — | Next.js + 6 页面 + API client |
| 9 | 前端页面 | ⬜ | — | — | 全功能交互 + SSE 集成 |
| 10 | 主题看板 | ⬜ | — | — | 6 套主题 + Chart.js 组件 |
| 11 | Docker | ⬜ | — | — | 7 服务 Compose |
| 12 | 测试文档 | ⬜ | — | — | ≥80% 覆盖率 + README + v2.0.0 |

### 执行规范（来自 CLAUDE.md Always Rules）

> **每完成一个 Step**：
> ① 执行 Step 中列出的所有「验证项」→ 全部通过
> ② 提示用户手动验证（浏览器操作 / API 测试）
> ③ 用户确认通过后，更新本表对应行（状态 → ✅，填写完成日期）
> ④ 更新 `.memory-bank/progress.md`
> ⑤ 才进入下一个 Step
>
> **禁止跳过 Step 或并行执行多个 Step。**

---

## 不在此阶段的范围

- ❌ 用户注册/登录系统（单用户版本）
- ❌ Amazon 爬虫直接抓取
- ❌ 多 ASIN 批量对比分析
- ❌ PDF 导出
- ❌ 分享链接（只读）
- ❌ 飞书/钉钉/企业微信通知
- ❌ Sorftime API 对接（Step 5 的 Phase 1 只实现 CSV 加载，Sorftime 作为后续扩展）
- ❌ 多语言 i18n
