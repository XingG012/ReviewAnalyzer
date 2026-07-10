# 项目架构文档

> 版本: v2.0 | 日期: 2026-07-10 | 状态: 初始骨架
>
> 本文档描述 ReviewAnalyzer v2.0 全栈版的代码架构、模块职责和数据流。
> 随着开发推进逐步补充细节。每完成一个里程碑后必须更新本文档。

---

## 一、高层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React SPA)                      │
│                                                               │
│  Next.js 15 (App Router)  ·  TypeScript strict                │
│  Tailwind CSS v4 + shadcn/ui  ·  Zustand + TanStack Query    │
│  Chart.js 4  ·  react-markdown + mermaid.js                   │
│  6 套主题: premium-gold / dark-tech / linear-minimal / ...    │
│                                                               │
│  职责: 页面路由 + 可视化看板 + SSE 进度消费 + 文件下载          │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (JSON) + SSE (text/event-stream)
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Backend (Python API)                        │
│                                                               │
│  FastAPI (ASGI)  ·  Uvicorn + Gunicorn                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  api/    │  │services/ │  │ models/  │  │  schemas/   │ │
│  │ 路由+校验 │─▶│ 业务逻辑  │─▶│ ORM 模型  │  │ Pydantic    │ │
│  │ 7 个模块 │  │ 4 个服务 │  │ 7 张表   │  │ 请求/响应    │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │
│                                                               │
│  Celery Worker (独立进程)                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ analysis_task.py: 5 Phase 分析流水线                   │    │
│  │  → 进度广播 (Redis Pub/Sub → SSE Manager)              │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL 16│ │   Redis 7    │ │    MinIO     │
│  任务/评论    │ │ 队列/缓存     │ │  CSV/报告    │
│  画像/报告    │ │ SSE Pub/Sub  │ │  文件存储    │
└──────────────┘ └──────────────┘ └──────────────┘
        ▲
        │ import（同进程复用）
┌───────┴─────────────────────────────────────────────────────┐
│          review-analyzer-skill/ （分析引擎，已有且不改动）       │
│                                                               │
│  src/                                                         │
│  ├── data_fetchers/     Phase 1: CSV + Sorftime 数据接入       │
│  ├── review_analyzer.py     Phase 2: 22维 AI 打标              │
│  ├── user_persona_analyzer  Phase 3: 用户画像识别               │
│  ├── insights_generator     Phase 4: 14章洞察报告              │
│  ├── output_manager.py      Phase 5: MD + HTML + CSV 输出      │
│  ├── template_engine.py     Jinja2 模板引擎 (6 套主题 HTML)    │
│  └── chart_engine.py        Chart.js 配置生成                   │
│                                                               │
│  AI 推理: Claude Code CLI (subprocess) — 零 API 成本           │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、模块职责

### 2.1 现有模块（复用，不改动）

| 目录/文件 | Phase | 职责 | 核心输入/输出 |
|-----------|-------|------|--------------|
| `src/data_fetchers/` | 1 | 数据接入层。`CsvFetcher` 读取 CSV，`SorftimeFetcher` 调 API | 输入: 文件路径或 ASIN → 输出: `list[dict]` 标准化评论 |
| `src/review_analyzer.py` | 2 | AI 打标引擎。ThreadPoolExecutor 并发，每批 20-50 条，失败重试 3 次 | 输入: 评论列表 → 输出: 带 22 维 tags + sentiment + info_score 的评论 |
| `src/user_persona_analyzer.py` | 3 | 场景×性别交叉画像识别。动态阈值，维度退化兜底 | 输入: tagged_reviews → 输出: personas (≤4) + golden_samples (每画像 3正+3负) |
| `src/insights_generator.py` | 4 | 14 章洞察报告 + 统计数据 + strategic_json | 输入: stats + personas + golden_samples → 输出: insights_md + strategic_json |
| `src/output_manager.py` | 5 | 统一输出调度：MD 写入 + HTML 渲染 + CSV 导出 + 飞书同步 | 输入: all artifacts → 输出: 文件路径 dict |
| `src/template_engine.py` | 5 | Jinja2 模板引擎：6 套主题，共享 base HTML + CSS | 输入: data + template_name → 输出: HTML 字符串 |
| `src/chart_engine.py` | 5 | Chart.js 配置生成（饼图、雷达图、柱状图、折线图） | 输入: stats → 输出: chart_configs dict (JSON) |
| `src/config.py` | 全局 | 全局配置单例。CLI 引擎探测，路径管理，环境变量读取 | — |
| `src/data_loader.py` | 1 | CSV 解析，列名模糊匹配，URL 下载 | 输入: 文件路径 → 输出: (reviews list, df) |
| `src/prompts/` | 2/4 | Prompt 模板管理。打标 Prompt + 报告生成 Prompt | — |

### 2.2 新建模块（backend/）

| 目录/文件 | 职责 | 依赖 |
|-----------|------|------|
| `app/main.py` | FastAPI 入口。CORS、路由注册、startup/shutdown 事件 | core, api |
| `app/core/config.py` | 配置管理。pydantic-settings，读取 `.env`，所有服务地址+密钥 | 无 |
| `app/core/database.py` | AsyncEngine + AsyncSession + `get_db` 依赖注入 | config, models |
| `app/api/router.py` | 路由汇总，注册所有子路由到 `/api` | 各 api 子模块 |
| `app/api/tasks.py` | `POST/GET/DELETE /api/tasks` + `/retry` + `/stream` (SSE) | services, schemas |
| `app/api/upload.py` | `POST /api/upload/csv` + `GET /api/upload/history` | services, schemas |
| `app/api/reviews.py` | `GET /api/tasks/{id}/reviews` + `/tagged` + `/personas` | services, schemas |
| `app/api/reports.py` | `GET /api/tasks/{id}/report` | services, schemas |
| `app/api/export.py` | `GET /api/tasks/{id}/export/{csv\|md\|html}` | services |
| `app/models/` | SQLAlchemy ORM 模型。7 张表：`tasks`, `reviews`, `tagged_reviews`, `personas`, `golden_samples`, `analysis_reports`, `uploads` | core.database |
| `app/schemas/` | Pydantic v2 请求/响应 Schema。`TaskCreate`, `TaskResponse`, `ReportResponse` 等 | 无（纯数据模型） |
| `app/services/task_service.py` | 任务 CRUD 业务逻辑。校验、创建、查询、删除、重试 | models, schemas |
| `app/services/pipeline_service.py` | 分析流程编排。触发 Celery 任务，不直接执行 | tasks.celery_app |
| `app/services/storage_service.py` | MinIO 文件存储。上传、下载、删除、预签名 URL | config, minio SDK |
| `app/services/sse_manager.py` | SSE 连接管理。订阅/取消订阅/广播，通过 Redis Pub/Sub 跨进程同步 | config, redis |
| `app/tasks/celery_app.py` | Celery 实例。Broker (Redis) + Result Backend (Redis) + 配置 | config |
| `app/tasks/analysis_task.py` | 5 Phase 分析 Celery 任务。调用 review-analyzer-skill 各模块，进度广播 | models, services, review-analyzer-skill |

### 2.3 新建模块（frontend/）

| 目录/文件 | 职责 |
|-----------|------|
| `src/app/` | Next.js App Router 页面。7 个路由：`/`, `/tasks`, `/tasks/new`, `/tasks/[id]`, `/tasks/[id]/report`, `/tasks/[id]/reviews`, `/export/[id]` |
| `src/components/layout/` | 全局布局组件：Navbar（导航+主题切换）、Container |
| `src/components/tasks/` | 任务相关组件：TaskCard、TaskList、CreateForm、ProgressBar |
| `src/components/dashboard/` | 看板可视化组件：StatCards、PieChart、RadarChart、BarChart、LineChart、PersonaCard、TagCloud |
| `src/components/themes/` | 6 套主题：ThemeProvider + 每套主题的 CSS token 定义文件 |
| `src/hooks/` | 自定义 Hook：`useTasks`、`useSSE`、`useReport`、`useReviews`、`usePersonas` |
| `src/stores/` | Zustand Store：`ui-store`（主题、侧边栏、Toast）、`task-draft-store`（新建任务草稿） |
| `src/lib/` | API Client（fetch 封装 + 类型化函数）、Zod validators（与后端 Pydantic 对齐）、工具函数 |

---

## 三、数据流

### 3.1 完整分析流程（端到端）

```
[用户] 上传 CSV + 输入 ASIN → 前端 POST /api/tasks
  │
  ▼
[FastAPI] task_service.create_task() → INSERT tasks (status=pending)
  │
  ├─ pipeline_service.start_analysis() → Celery task 入队
  │
  ▼
[Celery Worker] run_analysis_pipeline(task_id)
  │
  ├─ Phase 1: 从 MinIO 读取 CSV → load_reviews_from_file() → INSERT reviews
  │   ├─ SSE broadcast: {"event":"progress","data":{"phase":1,...}}
  │
  ├─ Phase 2: analyze_all(reviews) → 22维标签 → INSERT tagged_reviews
  │   ├─ SSE broadcast: {"event":"progress","data":{"phase":2,...}}
  │
  ├─ Phase 3: analyze_user_personas(tagged) → 画像+黄金样本 → INSERT personas + golden_samples
  │   ├─ SSE broadcast: {"event":"progress","data":{"phase":3,...}}
  │
  ├─ Phase 4: generate_insights(stats, personas, samples) → MD报告 → INSERT analysis_reports
  │   ├─ SSE broadcast: {"event":"progress","data":{"phase":4,...}}
  │
  ├─ Phase 5: generate_outputs(data, config) → HTML看板 → UPDATE analysis_reports
  │   ├─ 上传 CSV/MD/HTML 文件到 MinIO
  │   ├─ SSE broadcast: {"event":"done","data":{...}}
  │
  └─ UPDATE tasks SET status='done', progress=100
```

### 3.2 Phase 间数据传递

| 转换 | 输入 | 输出 | 存储位置 |
|------|------|------|---------|
| P1→P2 | 标准化评论 list[dict] | 带标签的评论 | 内存 → `tagged_reviews` 表 |
| P2→P3 | tagged_reviews | personas + golden_samples | 内存 → `personas` + `golden_samples` 表 |
| P2+P3→P4 | stats + personas + samples | insights_md + strategic_json | 内存 → `analysis_reports` 表 |
| P4→P5 | all artifacts | HTML + 文件 | 内存 → MinIO + `analysis_reports` 表 |

> 前 4 个 Phase 在 Celery Worker 内存中通过 Python 对象传递，不写临时文件。
> 只有 Phase 5 才产出持久化文件（上传到 MinIO）。

### 3.3 SSE 跨进程通信

```
Celery Worker (独立进程)
  │
  │  进度事件 (Redis Pub/Sub)
  │  PUBLISH channel:task:{task_id} {"event":"progress","data":{...}}
  ▼
Redis 7
  │
  │  SUBSCRIBE channel:task:{task_id}
  ▼
FastAPI 进程 (SSE Manager)
  │
  │  broadcast → asyncio.Queue → StreamingResponse
  ▼
前端 EventSource 连接
```

---

## 四、关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| **方案** | FastAPI + Celery (非 Django/Flask) | 异步原生 + 自动 API 文档 + Pydantic v2；分析长任务必须 Celery 解耦 |
| **数据库** | PostgreSQL 16 JSONB (非 MongoDB) | 强关系数据需要外键约束；JSONB 满足灵活标签 schema；减少运维复杂度 |
| **文件存储** | MinIO (非本地文件系统) | S3 兼容，单容器零运维；Celery Worker 和 API 进程共享文件访问 |
| **SSE 跨进程** | Redis Pub/Sub (非内存队列) | Celery Worker 独立进程，无法共享 FastAPI 内存；Redis 已作为 Broker 存在，复用基础设施 |
| **前后端校验** | Zod ↔ Pydantic (双向对齐) | 前后端共享同一套校验规则，类型自动推导，减少不一致 bug |
| **AI 引擎** | Claude CLI subprocess (非 API) | 零成本；prompt 不限长度；复用现有 22 维标签体系 |
| **6 套主题** | CSS 变量体系 (非每套独立 CSS) | 一套 React 组件 + 6 套 CSS token，新增主题只需 ~100 行 |
| **包管理** | uv (Python) + pnpm (Node) | 速度快 10-100x；严格依赖隔离；前后端理念统一 |

---

## 五、目录结构

```
ReviewAnalyzer/
│
├── review-analyzer-skill/          # ▲ 分析引擎（已有，不改动）
│   ├── main.py                     # CLI 入口
│   ├── SKILL.md
│   └── src/
│       ├── config.py               # 全局配置单例
│       ├── data_fetchers/          # CSV + Sorftime 数据接入
│       ├── review_analyzer.py      # Phase 2: AI 打标
│       ├── user_persona_analyzer.py# Phase 3: 用户画像
│       ├── insights_generator.py   # Phase 4: 洞察报告
│       ├── output_manager.py       # Phase 5: 输出管理
│       ├── template_engine.py      # Jinja2 模板引擎
│       ├── chart_engine.py         # Chart.js 配置
│       ├── prompts/                # Prompt 模板
│       └── templates/              # 6 套 HTML 主题模板
│
├── backend/                        # ▲ 新建: FastAPI 后端
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── core/                   # 配置 + 数据库引擎
│   │   ├── api/                    # 路由层 (7 个模块)
│   │   ├── models/                 # SQLAlchemy ORM (7 张表)
│   │   ├── schemas/                # Pydantic 校验
│   │   ├── services/               # 业务逻辑 (4 个服务)
│   │   └── tasks/                  # Celery 任务
│   ├── alembic/                    # 数据库迁移
│   ├── tests/                      # pytest
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/                       # ▲ 新建: Next.js 前端
│   ├── src/
│   │   ├── app/                    # 7 个路由页面
│   │   ├── components/             # 组件 (layout/tasks/dashboard/themes)
│   │   ├── hooks/                  # 自定义 Hook
│   │   ├── stores/                 # Zustand
│   │   ├── lib/                    # API client + validators
│   │   └── styles/                 # Tailwind + 主题变量
│   ├── tests/                      # Vitest
│   ├── e2e/                        # Playwright
│   ├── package.json
│   ├── tsconfig.json
│   ├── biome.json
│   └── Dockerfile
│
├── .memory-bank/                   # 项目文档（AI 编码引导）
│   ├── PRD.md                      # 产品需求
│   ├── tech_stack.md               # 技术选型
│   ├── architecture.md             # ← 本文件
│   ├── implementation_plan.md      # 实施计划
│   └── progress.md                 # 进度跟踪
│
├── docker-compose.yml              # 7 服务编排
├── nginx.conf                      # 反向代理
├── .env.example                    # 环境变量模板
├── CLAUDE.md                       # AI 编码规则
└── README.md
```

---

## 六、待补充（随开发推进）

以下内容将在对应 Step 完成后填入：

- [ ] Step 2 完成后：完整数据库 ER 图 + 索引策略说明
- [ ] Step 5 完成后：Celery 任务状态机 + 重试策略流程图
- [ ] Step 6 完成后：SSE 事件类型定义 + 重连策略
- [ ] Step 8 完成后：前端组件树完整层级图
- [ ] Step 10 完成后：6 套主题 CSS token 对照表
- [ ] Step 11 完成后：Docker 网络拓扑 + 数据卷挂载图
