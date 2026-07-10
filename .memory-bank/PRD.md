# ReviewAnalyzer — 产品需求文档 (PRD)

> 版本: v2.0 | 日期: 2026-07-10 | 状态: 已确认
>
> 本文档定义 ReviewAnalyzer 全栈版（React SPA + FastAPI + PostgreSQL）完整产品需求。
> 采用详细工程级粒度，包含数据库 DDL、API Schema、前端组件树、状态管理设计，
> 可直接作为全栈项目简历作品的核心设计文档。

---

## 目录

1. [产品概述](#一产品概述)
2. [功能需求](#二功能需求)
3. [技术架构](#三技术架构)
4. [数据库设计](#四数据库设计)
5. [API 设计](#五api-设计)
6. [前端设计](#六前端设计)
7. [数据流与状态管理](#七数据流与状态管理)
8. [部署架构](#八部署架构)
9. [非功能需求](#九非功能需求)
10. [测试策略](#十测试策略)
11. [里程碑规划](#十一里程碑规划)
12. [风险与缓解](#十二风险与缓解)
13. [附录](#十三附录)

---

## 一、产品概述

### 1.1 产品定位

**ReviewAnalyzer** 是面向跨境电商运营人员的 Amazon 评论深度分析平台。

用户输入商品 ASIN 或上传评论 CSV，系统自动获取评论数据，通过 Claude 大模型完成
22 维度智能打标与 14 章洞察报告生成，最终输出 6 套可切换主题的交互式可视化看板。

**一句话描述**：输入 ASIN，获得一份专业级产品评论洞察看板。

### 1.2 核心价值

| 痛点 | 解决方案 |
|------|---------|
| 手动翻 Amazon 评论效率低 | 一键抓取 + AI 自动分析 500 条评论 |
| 现有工具太贵（$39-$49/月） | MIT 开源，Docker 自托管，零月费 |
| AI 成本高（API Key 按 token 计费） | 利用用户 Claude Code 订阅配额，零 API 成本 |
| 分析维度浅（仅情感分析） | 22 维标签 × 14 章报告 × 用户画像，远超竞品 |
| 分析结果难以交付 | 6 套专业看板主题，适合不同汇报场景 |

### 1.3 目标用户

- **主要用户**：Amazon 卖家运营人员、产品经理、品牌方选品负责人
- **使用场景**：竞品分析、产品迭代决策、Listing 优化、市场调研报告
- **技术能力**：会使用 Docker 部署自托管服务，或直接使用本地 Python 环境

### 1.4 产品边界

**v2.0 包含**：
- ✅ CSV 上传 + Sorftime API 数据获取
- ✅ 5 Phase 分析流水线（复用现有 `review-analyzer-skill` 引擎）
- ✅ React SPA 前端（Next.js 15 + TypeScript）
- ✅ FastAPI 后端 + Celery 异步任务
- ✅ PostgreSQL + Redis + MinIO 数据层
- ✅ 6 套可视化看板主题（从 Jinja2 重写为 React 组件）
- ✅ CSV / Markdown / HTML 报告导出
- ✅ Docker Compose 一键部署

**v2.0 不包含**（后续迭代）：
- ❌ 用户注册/登录系统
- ❌ Amazon 爬虫直接抓取
- ❌ 多 ASIN 批量对比分析
- ❌ PDF 导出
- ❌ 分享链接
- ❌ 飞书/钉钉通知集成

---

## 二、功能需求

### 2.1 数据获取 (Data Fetching)

**两种数据源**：

| 数据源 | 描述 | 输入方式 | 适用场景 |
|--------|------|---------|---------|
| CSV 上传 | 用户上传评论 CSV 文件 | Web 文件上传 | 从其他工具导出的评论数据 |
| Sorftime API | 对接 Sorftime 平台 API | 输入 ASIN + API Key | 已有 Sorftime 订阅的用户 |

**CSV 上传规格**：
- 支持文件大小：≤ 50MB
- 支持列名模糊匹配（`review_text` / `body` / `comment` 均识别为评论正文）
- 上传后前端预览：前 10 行 + 统计摘要（总条数、评分范围）
- 文件持久化：MinIO 存储，数据库记录原始文件名和元数据

**Sorftime API 对接**：
- 通过 ASIN + 站点（US/UK/DE/JP）查询评论
- 单次最多返回 100 条
- 系统自动拉取多页以覆盖更多评论

### 2.2 分析任务管理

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 创建任务 | 选择数据源（CSV / Sorftime），配置 ASIN、站点、评论数上限、模板 | P0 |
| 任务进度 | 实时展示 Phase 1→5 进度（SSE 推送），每 Phase 有 emoji + 中文描述 | P0 |
| 任务列表 | 首页仪表盘展示所有历史任务，支持按状态筛选 | P0 |
| 任务详情 | 查看完整分析结果：看板 + 报告 + 打标数据 | P0 |
| 删除任务 | 软删除或物理删除任务及关联数据 | P1 |
| 重试任务 | 失败任务一键重新分析 | P1 |

**任务状态机**：

```
pending → fetching → tagging → analyzing → rendering → done
                ↓         ↓          ↓           ↓
              failed    failed     failed      failed
```

### 2.3 AI 分析引擎（五阶段流水线）

> 完整复用 `review-analyzer-skill/src/` 现有模块，零改造。

| Phase | 模块文件 | 输入 | 输出 | 耗时估算 |
|-------|---------|------|------|---------|
| **P1** 数据获取 | `data_fetchers/` | CSV 路径 或 Sorftime 配置 | `List[Dict]` 标准化评论 | 1-30s |
| **P2** AI 打标 | `review_analyzer.py` | 标准化评论列表 | 带 22 维标签的评论 | 5-10min (500条) |
| **P3** 用户画像 | `user_persona_analyzer.py` | 打标评论 | 4 个画像 + 黄金样本 | 1-2min |
| **P4** 洞察报告 | `insights_generator.py` | 统计 + 画像 + 样本 | 14 章 MD 报告 | 2-3min |
| **P5** 输出看板 | `output_manager.py` | 全部产物 | HTML + CSV + MD 文件 | 5-15s |

**AI 调用方案**：

```
Claude Code CLI (subprocess)
  └── claude --print --dangerously-skip-permissions <prompt>

优点：
  - 零 API Key 成本（利用用户 Claude Code 订阅配额）
  - 零配置（claude CLI 已安装即可）
  - prompt 长度不受 API context window 限制
  - 直接复用现有 22 维度 Prompt 体系和标签系统

重试策略：
  - 每批次失败自动重试 3 次
  - 超时时间 600s/批次
  - 并发批次数上限 4 (ThreadPoolExecutor)
```

### 2.4 可视化看板

**6 套主题**（从 Jinja2 模板重写为 React 组件）：

| 主题 ID | 名称 | 风格 | 适用场景 |
|---------|------|------|---------|
| `premium-gold` | Premium Gold | 黑金奢华 + Playfair Display 字体 | 高管汇报、品牌展示 |
| `dark-tech` | Dark Tech | 赛博朋克 + 青色霓虹 + 毛玻璃 | 技术团队、数据密集 |
| `linear-minimal` | Linear Minimal | 极简白蓝 + 清透玻璃 | 产品评审、简洁汇报 |
| `posthog-analytics` | PostHog Analytics | 暖白橙色 + 暖色玻璃 | 运营复盘、增长分析 |
| `stripe-executive` | Stripe Executive | 翡翠绿 + 金融企业风 | 金融报告、投资决策 |
| `warm-editorial` | Warm Editorial | 纸色铜色 + 编辑风格 | 品牌报告、阅读分享 |

**主题架构**（共享基座模式）：

```
themes/
├── base/
│   ├── tokens.css          ← CSS 自定义属性（--color-primary, --font-heading...）
│   └── base-components.tsx ← 共享 UI 组件（指标卡、图表容器、标签云）
├── premium-gold/
│   ├── theme.css           ← 仅覆盖 CSS 变量（约 100 行）
│   └── meta.json           ← 主题元数据
├── dark-tech/
│   └── ...
```

**看板包含的可视化模块**：
- 指标卡片行（总评论数、平均评分、情感分布、画像数）
- 情感分布饼图（Chart.js）
- 22 维标签雷达图
- 用户画像卡片（画像名 + 人数 + 特征标签 + 黄金样本引用）
- 月度评分趋势折线图
- 信息价值评分分布直方图
- TOP 标签柱状图
- 关键词词云

### 2.5 报告导出

| 格式 | 内容 | 说明 |
|------|------|------|
| **CSV** | 打标数据完整表（原始列 + 22 维标签列 + 信息评分） | UTF-8 BOM 编码，Excel 友好 |
| **Markdown** | 14 章洞察报告全文（含 Mermaid 图表源码） | 可用 Typora / Obsidian 打开 |
| **HTML** | 完整可视化看板（自包含，离线可打开） | 内嵌 CSS + Chart.js CDN |

---

## 三、技术架构

### 3.1 架构全景图

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React SPA)                      │
│                                                               │
│  Next.js 15 + TypeScript strict + Tailwind CSS v4             │
│  shadcn/ui (基础组件) + Chart.js 4 (图表)                      │
│  Zustand (UI 状态) + TanStack Query v5 (服务端缓存)            │
│  Zod (Schema 校验，与后端 Pydantic 对齐)                       │
│  react-markdown + mermaid.js (报告渲染)                        │
│  Vitest + React Testing Library + Playwright (测试)            │
│  Biome (lint + format)                                        │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST + SSE
                        │ Content-Type: application/json
                        │ (SSE: text/event-stream)
┌───────────────────────▼─────────────────────────────────────┐
│                    Backend (Python API)                        │
│                                                               │
│  FastAPI + Uvicorn (ASGI)                                     │
│  SQLAlchemy 2.0 + asyncpg (PostgreSQL)                        │
│  Pydantic v2 (请求/响应 校验)                                  │
│  Celery + Redis (异步任务队列)                                 │
│  Alembic (数据库迁移)                                          │
│  SSE (Server-Sent Events, 实时推送任务进度)                    │
│  structlog (结构化日志)                                        │
│  pytest + httpx (测试)                                        │
│  ruff + mypy (代码质量)                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL 16│ │   Redis 7    │ │    MinIO     │
│   (主存储)    │ │ (队列/缓存)   │ │  (文件存储)   │
└──────────────┘ └──────────────┘ └──────────────┘
        ▲
        │ import（同进程）
┌───────┴─────────────────────────────────────────────────────┐
│              review-analyzer-skill（分析引擎）                  │
│                                                               │
│  src/                                                         │
│  ├── data_fetchers/    (CSV + Sorftime)                       │
│  ├── review_analyzer.py   (Phase 2: AI 打标)                   │
│  ├── user_persona_analyzer.py (Phase 3: 用户画像)              │
│  ├── insights_generator.py    (Phase 4: 洞察报告)              │
│  ├── output_manager.py        (Phase 5: 输出管理)              │
│  ├── template_engine.py       (Jinja2 SSR，Phase 5 复用)       │
│  └── chart_engine.py          (Chart.js 配置生成)              │
│                                                               │
│  AI 引擎: Claude Code CLI (subprocess)                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 技术选型与决策记录

#### 前端

| 技术 | 选型 | 决策理由 |
|------|------|---------|
| **框架** | Next.js 15 (App Router, SPA) | 生态成熟；分享链接功能可选择性 SSR；Docker 自托管 `next start` 即可 |
| **语言** | TypeScript (strict) | 类型安全 + IDE 智能提示，团队协作与重构信心保障 |
| **CSS** | Tailwind CSS v4 + shadcn/ui | 原子化 CSS 开发效率高；shadcn/ui 无依赖、可定制、Tree-shakable |
| **状态管理** | Zustand + TanStack Query v5 | Zustand (~1KB) 管理 UI 状态；TanStack Query 处理服务端缓存/失效/重试 |
| **图表** | Chart.js 4 + react-chartjs-2 | 与现有 6 套模板 Chart.js 配置完全复用，零迁移成本 |
| **表单校验** | Zod | 前后端 Schema 对齐（Zod ↔ Pydantic），类型自动推导 |
| **Markdown** | react-markdown + mermaid.js | 渲染 14 章报告 + 流程图/象限图客户端实时渲染 |
| **测试** | Vitest + Playwright | Vite 原生速度；Playwright 多浏览器 E2E |
| **代码质量** | Biome | 单一二进制替代 ESLint + Prettier，快 10x+ |
| **包管理** | pnpm | 硬链接省磁盘，严格依赖隔离防幽灵依赖 |

#### 后端

| 技术 | 选型 | 决策理由 |
|------|------|---------|
| **语言** | Python 3.13 | 与现有分析引擎同语言，直接 import 复用所有模块 |
| **Web 框架** | FastAPI | 异步原生支持；自动生成 Swagger 文档；Pydantic v2 深度集成 |
| **ASGI** | Uvicorn + Gunicorn | 生产级多 worker 并发 |
| **ORM** | SQLAlchemy 2.0 (async) | Python 生态标准；2.0 原生 async/await；FastAPI 配合好 |
| **迁移** | Alembic | SQLAlchemy 官方迁移工具，支持升级/降级 |
| **任务队列** | Celery + Redis | Python 异步任务标准方案；分析耗时 5-15min 必须异步 |
| **文件存储** | MinIO | S3 兼容，Docker 单容器部署，自托管零成本 |
| **日志** | structlog | 结构化 JSON 日志，`docker logs` 直接查看，零外部依赖 |
| **测试** | pytest + pytest-asyncio + httpx | Python 测试标准 |
| **代码质量** | ruff + mypy (strict) | Rust 实现毫秒级；严格类型检查 |

**为什么是 Celery 而不是直接在 FastAPI 里后台线程跑？**
- 分析任务耗时 5-15 分钟，需独立 worker 进程避免阻塞 API
- Celery 提供重试、超时、优先级等任务生命周期管理
- 与 FastAPI 通过 Redis 解耦，可独立扩缩 worker 数量

**为什么不直接用 Anthropic API 替代 CLI subprocess？**
- CLI 模式利用用户已有 Claude Code 订阅，项目零 AI 成本
- 符合"自托管 + 免费"的产品定位
- 长期可通过配置支持双模式（CLI / API Key）

### 3.3 模块分层

```
backend/
├── app/
│   ├── main.py                  # FastAPI 入口 + CORS + 生命周期
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   └── database.py          # AsyncSession + engine
│   ├── api/
│   │   ├── router.py            # 路由汇总
│   │   ├── deps.py              # 公共依赖注入（get_db 等）
│   │   ├── tasks.py             # POST/GET/DELETE /api/tasks
│   │   ├── reviews.py           # GET /api/tasks/{id}/reviews
│   │   ├── reports.py           # GET /api/tasks/{id}/report
│   │   ├── export.py            # GET /api/tasks/{id}/export/*
│   │   └── upload.py            # POST /api/upload/csv
│   ├── models/
│   │   ├── task.py              # Task SQLAlchemy 模型
│   │   ├── review.py            # Review + TaggedReview 模型
│   │   ├── persona.py           # Persona + GoldenSample 模型
│   │   └── report.py            # AnalysisReport 模型
│   ├── schemas/
│   │   ├── task.py              # TaskCreate/Update/Response Pydantic
│   │   ├── review.py            # ReviewResponse Pydantic
│   │   ├── persona.py           # PersonaResponse Pydantic
│   │   └── report.py            # ReportResponse Pydantic
│   ├── services/
│   │   ├── task_service.py      # 任务 CRUD 业务逻辑
│   │   ├── pipeline_service.py  # 分析流程编排（产消进度 → SSE）
│   │   ├── storage_service.py   # MinIO 文件上传/下载
│   │   └── sse_manager.py       # SSE 连接管理与广播
│   ├── tasks/                   # Celery 任务
│   │   ├── celery_app.py        # Celery 实例
│   │   └── analysis_task.py     # 分析任务定义
│   └── utils/
│       └── asin_utils.py        # ASIN 校验工具
├── alembic/                     # 数据库迁移
│   ├── env.py
│   └── versions/
├── requirements.txt
└── Dockerfile
```

**模块约束**（继承 CLAUDE.md 规则）：
- 每个文件 ≤ 500 行
- 禁止创建 `utils.py` / `helpers.py` 等万能杂物间文件
- API 请求/响应必须用 Pydantic 校验
- 敏感信息只能出现在 `.env` 中

---

## 四、数据库设计

### 4.1 ER 图

```
┌──────────┐
│  tasks   │ 1 ────────── N ┌─────────┐
│          │                │ reviews  │
│ id (PK)  │                │          │
│ asin     │                │ id (PK)  │
│ site     │                │ task_id  │──┐
│ status   │                │ ...      │  │
│ ...      │                └─────────┘  │
└──────────┘                             │
      │ 1                                │
      │                                  │
      ├── N ┌──────────────┐             │
      │     │tagged_reviews│ N ──── 1 ───┘
      │     │              │
      │     │ id (PK)      │
      │     │ task_id (FK) │
      │     │ review_id(FK)│
      │     │ tags (JSONB) │
      │     │ ...          │
      │     └──────────────┘
      │
      ├── N ┌──────────────┐
      │     │   personas   │
      │     │              │
      │     │ id (PK)      │
      │     │ task_id (FK) │
      │     │ name         │
      │     │ ...          │
      │     └──────┬───────┘
      │            │ 1
      │            │
      │     ┌──────▼───────────┐
      │     │  golden_samples  │
      │     │                  │
      │     │ id (PK)          │
      │     │ task_id (FK)     │
      │     │ persona_id (FK)  │
      │     │ review_id (FK) ──┼── 1 ── [reviews]
      │     │ sentiment        │
      │     └──────────────────┘
      │
      └── 1 ┌──────────────────┐
            │ analysis_reports │
            │                  │
            │ id (PK)          │
            │ task_id (FK,UQ)  │
            │ insights_md      │
            │ html_content     │
            │ ...              │
            └──────────────────┘
```

### 4.2 完整 DDL

```sql
-- ============================================================
-- 1. 分析任务表
-- ============================================================
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin            VARCHAR(20)  NOT NULL,
    site            VARCHAR(5)   NOT NULL DEFAULT 'US',
    source          VARCHAR(20)  NOT NULL DEFAULT 'csv',
        -- 'csv' | 'sorftime'

    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
        -- 'pending' | 'fetching' | 'tagging' | 'analyzing'
        -- | 'rendering' | 'done' | 'failed'

    progress        SMALLINT     NOT NULL DEFAULT 0,
        -- 0-100 整体进度百分比

    current_phase   SMALLINT     NOT NULL DEFAULT 0,
        -- 1-5 当前 Phase 编号

    phase_message   TEXT,
        -- 当前阶段的详细描述，用于 SSE 推送

    -- 输入配置（JSON 快照，便于复现）
    config          JSONB        NOT NULL DEFAULT '{}',
        /*
        {
          "max_reviews": 500,
          "batch_size": 20,
          "template": "premium-gold",
          "uploaded_file": "reviews_2025.csv",
          "sorftime_api_key_hash": "sha256:xxx"  // 仅存哈希，不存原文
        }
        */

    -- 结果摘要（冗余字段，避免每次查报告表）
    total_reviews   INTEGER      NOT NULL DEFAULT 0,
    persona_count   INTEGER      NOT NULL DEFAULT 0,
    avg_rating      FLOAT,

    -- 时间戳
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- 错误信息
    error_message   TEXT,
    error_phase     SMALLINT
);

-- 索引
CREATE INDEX idx_tasks_status     ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_asin       ON tasks(asin);

-- 约束
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_status
    CHECK (status IN ('pending','fetching','tagging','analyzing','rendering','done','failed'));
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_source
    CHECK (source IN ('csv','sorftime'));
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_site
    CHECK (site IN ('US','UK','DE','JP'));
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_progress
    CHECK (progress BETWEEN 0 AND 100);


-- ============================================================
-- 2. 原始评论表
-- ============================================================
CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID         NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

    -- Amazon 原始数据
    review_id       VARCHAR(50),    -- Amazon 原始 review_id
    title           TEXT,
    body            TEXT         NOT NULL,
    rating          FLOAT        NOT NULL,
    author          VARCHAR(200),
    date            DATE,
    helpful_count   INTEGER      DEFAULT 0,
    verified_purchase BOOLEAN    DEFAULT FALSE,
    images          JSONB,          -- ["https://...", ...]
    variant         VARCHAR(200),   -- 变体信息（颜色/尺寸等）
    country         VARCHAR(10),    -- 评论来源站点

    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_reviews_task_id   ON reviews(task_id);
CREATE INDEX idx_reviews_rating    ON reviews(rating);
CREATE INDEX idx_reviews_date      ON reviews(date);
CREATE UNIQUE INDEX idx_reviews_unique
    ON reviews(task_id, review_id) WHERE review_id IS NOT NULL;


-- ============================================================
-- 3. AI 打标结果表
-- ============================================================
CREATE TABLE tagged_reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID         NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    review_id       UUID         NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,

    -- AI 打标结果
    sentiment       VARCHAR(20),    -- '积极' | '中性' | '消极'
    info_score      SMALLINT     NOT NULL DEFAULT 0,
        -- 评论信息价值评分 0-10

    -- 22 维度标签（JSONB 存储，灵活查询）
    tags            JSONB        NOT NULL DEFAULT '{}',
        /*
        {
          "人群_性别": "男性",
          "人群_年龄段": "25-35岁",
          "使用_场景": "家用",
          "使用_时长": "3-6个月",
          "产品_质量": "满意",
          "产品_性价比": "高",
          ...
        }
        */

    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_tagged_task_id       ON tagged_reviews(task_id);
CREATE INDEX idx_tagged_review_id     ON tagged_reviews(review_id);
CREATE INDEX idx_tagged_sentiment     ON tagged_reviews(sentiment);
CREATE INDEX idx_tagged_tags          ON tagged_reviews USING GIN (tags);
    -- GIN 索引支持 JSONB 内字段查询（如 tags->>'人群_性别' = '女性'）


-- ============================================================
-- 4. 用户画像表
-- ============================================================
CREATE TABLE personas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID         NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

    name            VARCHAR(100) NOT NULL,
        -- 画像名，如 "家用_女性"、"户外_男性"

    count           INTEGER      NOT NULL DEFAULT 0,
        -- 该画像覆盖的评论人数

    dimension       VARCHAR(50),
        -- 交叉维度，如 "场景_性别"

    tags            JSONB        NOT NULL DEFAULT '{}',
        -- 画像特征标签 {"场景": "家用", "性别": "女性", "年龄段": "25-35"}

    color           VARCHAR(7)   NOT NULL DEFAULT '#6366f1',
        -- 前端展示颜色 (hex)

    summary         TEXT,
        -- AI 生成的画像一句话概括

    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_personas_task_id ON personas(task_id);


-- ============================================================
-- 5. 黄金样本表
-- ============================================================
CREATE TABLE golden_samples (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID         NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    persona_id      UUID         NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    review_id       UUID         NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,

    sentiment       VARCHAR(20),
        -- 'positive' | 'negative'

    sentiment_class VARCHAR(20),
        -- 更细粒度的情感分类

    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_golden_task_id    ON golden_samples(task_id);
CREATE INDEX idx_golden_persona_id ON golden_samples(persona_id);


-- ============================================================
-- 6. 分析报告表
-- ============================================================
CREATE TABLE analysis_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID         NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,

    -- 洞察报告（14 章 Markdown 全文）
    insights_md     TEXT,

    -- 统计数据快照（JSONB）
    stats           JSONB,
        /*
        {
          "total_reviews": 500,
          "avg_rating": 4.2,
          "sentiment": {"积极": 312, "中性": 120, "消极": 68},
          "top_tags": {"产品_质量": 423, "产品_性价比": 389, ...},
          "dimensional_stats": {...}
        }
        */

    -- 战略数据
    strategic_json  JSONB,
        -- {"moat": [...], "weakness": [...], "action_matrix": [...]}

    -- 图表配置（供前端 Chart.js 直接消费）
    chart_configs   JSONB,

    -- 渲染后的 HTML 看板（Jinja2 服务端渲染）
    html_content    TEXT,

    -- 元数据
    template_name   VARCHAR(50)  NOT NULL DEFAULT 'premium-gold',
    md_word_count   INTEGER,
    generated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_task_id ON analysis_reports(task_id);


-- ============================================================
-- 7. 上传文件记录表
-- ============================================================
CREATE TABLE uploads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_name   VARCHAR(500) NOT NULL,
    stored_path     VARCHAR(1000) NOT NULL,
        -- MinIO object key 或本地文件路径（Phase 1 兼容）

    size_bytes      BIGINT       NOT NULL DEFAULT 0,
    review_count    INTEGER      NOT NULL DEFAULT 0,
    storage_backend VARCHAR(20)  NOT NULL DEFAULT 'minio',
        -- 'minio' | 'local'

    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_uploads_created_at ON uploads(created_at DESC);


-- ============================================================
-- 自动更新 updated_at 触发器
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### 4.3 数据库选型说明

| 决策 | 选型 | 理由 |
|------|------|------|
| 主键类型 | UUID | 分布式友好，避免自增 ID 暴露数据量 |
| 标签存储 | JSONB | 22 维度标签字段会迭代，JSONB 无需改表结构；支持 GIN 索引查询 |
| 配置快照 | JSONB | 分析配置可能扩展（新参数），JSONB 灵活存储且不需要 JOIN |
| 任务-报告 | 1:1 UNIQUE | 一个任务只产生一份报告，UNIQUE 约束保证数据完整性 |
| 外键策略 | ON DELETE CASCADE | 删除任务时自动清理所有关联数据 |
| 文本字段 | TEXT (非 VARCHAR) | PostgreSQL 中 TEXT 和 VARCHAR 性能无差异，TEXT 更灵活 |

---

## 五、API 设计

### 5.1 通用约定

| 项目 | 规范 |
|------|------|
| Base URL | `http://localhost:8000/api` |
| 认证 | 无（单用户版） |
| Content-Type | `application/json`（文件上传用 `multipart/form-data`） |
| 字符编码 | UTF-8 |
| 分页 | Query 参数 `offset` + `limit`，默认 `limit=20, max=100` |
| 错误响应格式 | `{"detail": "错误描述", "error_code": "TASK_NOT_FOUND"}` |
| 时间格式 | ISO 8601 (`2026-07-10T14:30:00+08:00`) |
| SSE 端点 | `Accept: text/event-stream`，事件类型 `progress` / `done` / `error` |

### 5.2 完整 API 端点

#### 5.2.1 系统

```
GET /api/health
  → 200 { "status": "ok", "version": "2.0.0", "claude_cli_available": true }
```

#### 5.2.2 文件上传

```
POST /api/upload/csv
  Content-Type: multipart/form-data
  Body:
    file: CSV 文件 (binary)
  → 201 {
       "upload_id": "uuid",
       "original_name": "reviews_2025.csv",
       "size_bytes": 2048000,
       "review_count": 480,
       "preview_rows": [ {...}, {...} ]   // 前 10 行预览
     }
  → 400 { "detail": "请上传 CSV 格式的文件 (最大 50MB)" }

GET /api/upload/history
  ?limit=20
  → 200 { "uploads": [ {...}, ... ], "total": 15 }
```

#### 5.2.3 分析任务

```
POST /api/tasks
  Body (JSON):
  {
    "asin": "B0DGV4T6BK",
    "site": "US",
    "source": "csv",              // "csv" | "sorftime"
    "upload_id": "uuid",          // source=csv 时必填
    "config": {                   // 可选，有默认值
      "max_reviews": 500,
      "batch_size": 20,
      "template": "premium-gold"
    },
    "sorftime_config": {          // source=sorftime 时必填
      "api_key": "sk-xxx"         // 仅内存使用，不落库
    }
  }
  → 201 { "task_id": "uuid", "status": "pending", "created_at": "..." }
  → 400 { "detail": "ASIN 格式不正确：B0DGV4T..." }

GET /api/tasks
  ?status=done                    // 可选筛选
  &offset=0&limit=20              // 分页
  → 200 {
       "tasks": [
         {
           "id": "uuid",
           "asin": "B0DGV4T6BK",
           "site": "US",
           "status": "done",
           "progress": 100,
           "total_reviews": 480,
           "persona_count": 4,
           "template": "premium-gold",
           "created_at": "...",
           "completed_at": "..."
         }, ...
       ],
       "total": 25
     }

GET /api/tasks/{task_id}
  → 200 { 完整任务详情 + 结果摘要 }
  → 404 { "detail": "任务不存在" }

DELETE /api/tasks/{task_id}
  → 204 (No Content)
  → 404 { "detail": "任务不存在" }

POST /api/tasks/{task_id}/retry
  → 202 { "task_id": "uuid", "status": "pending", "message": "任务已重新入队" }
  → 409 { "detail": "任务正在进行中，无法重试" }
```

#### 5.2.4 任务数据查询

```
GET /api/tasks/{task_id}/reviews
  ?offset=0&limit=50
  &rating_min=3&rating_max=5      // 评分筛选
  &sentiment=积极                 // 情感筛选
  → 200 { "reviews": [...], "total": 480 }

GET /api/tasks/{task_id}/tagged
  ?tag_key=人群_性别&tag_value=女性  // 标签筛选
  &offset=0&limit=50
  → 200 { "tagged_reviews": [...], "total": 120 }

GET /api/tasks/{task_id}/personas
  → 200 {
       "personas": [
         {
           "id": "uuid",
           "name": "家用_女性",
           "count": 145,
           "tags": {"场景": "家用", "性别": "女性"},
           "color": "#ec4899",
           "summary": "以家庭使用场景为主的女性用户群体...",
           "golden_samples": [
             {
               "review_body": "买来给家人用，...",
               "sentiment": "positive",
               "rating": 5
             }, ...
           ]
         }, ...
       ]
     }

GET /api/tasks/{task_id}/report
  → 200 {
       "insights_md": "# 分析洞察报告\n\n...",
       "stats": { "avg_rating": 4.2, ... },
       "chart_configs": { ... },
       "html_content": "<!DOCTYPE html>...",
       "template_name": "premium-gold",
       "generated_at": "..."
     }
  → 404 { "detail": "报告尚未生成" }
```

#### 5.2.5 文件导出

```
GET /api/tasks/{task_id}/export/csv
  → 200  Content-Type: text/csv; charset=utf-8
        Content-Disposition: attachment; filename="B0DGV4T6BK_打标数据.csv"

GET /api/tasks/{task_id}/export/md
  → 200  Content-Type: text/markdown; charset=utf-8
        Content-Disposition: attachment; filename="B0DGV4T6BK_洞察报告.md"

GET /api/tasks/{task_id}/export/html
  → 200  Content-Type: text/html; charset=utf-8
        Content-Disposition: attachment; filename="B0DGV4T6BK_看板.html"
```

#### 5.2.6 SSE 实时进度

```
GET /api/tasks/{task_id}/stream
  Accept: text/event-stream
  
  Event Stream:
    event: progress
    data: {"phase": 1, "phase_name": "数据获取", "message": "正在加载评论...", "progress": 10}

    event: progress
    data: {"phase": 2, "phase_name": "AI打标", "message": "已完成 45/100 条打标", "progress": 35}

    event: progress
    data: {"phase": 3, "phase_name": "用户画像", "message": "正在识别画像...", "progress": 55}

    event: progress
    data: {"phase": 4, "phase_name": "洞察报告", "message": "正在生成14章报告...", "progress": 75}

    event: progress
    data: {"phase": 5, "phase_name": "输出看板", "message": "渲染可视化看板...", "progress": 95}

    event: done
    data: {"task_id": "uuid", "status": "done", "total_reviews": 480}

    event: error
    data: {"phase": 2, "message": "AI 打标超时，请减少分析数量后重试"}
```

### 5.3 Pydantic Schema 定义（核心）

```python
# schemas/task.py

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal
import re

class TaskConfig(BaseModel):
    """任务分析配置"""
    max_reviews: int = Field(default=500, ge=10, le=2000)
    batch_size: int = Field(default=20, ge=5, le=50)
    template: str = Field(default="premium-gold")

class TaskCreate(BaseModel):
    """创建任务请求"""
    asin: str = Field(min_length=10, max_length=10)
    site: Literal["US", "UK", "DE", "JP"] = "US"
    source: Literal["csv", "sorftime"] = "csv"
    upload_id: Optional[UUID] = None    # source=csv 时必填
    config: TaskConfig = TaskConfig()

    @field_validator("asin")
    @classmethod
    def validate_asin(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9]{10}$", v.upper()):
            raise ValueError(f"ASIN 格式不正确：{v}")
        return v.upper()

class TaskResponse(BaseModel):
    """任务响应"""
    id: UUID
    asin: str
    site: str
    source: str
    status: str
    progress: int
    current_phase: int
    phase_message: Optional[str]
    total_reviews: int
    persona_count: int
    avg_rating: Optional[float]
    template: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[TaskResponse]
    total: int
```

### 5.4 SSE 管理器设计

```python
# services/sse_manager.py

import asyncio
import json
from uuid import UUID
from typing import Dict

class SSEManager:
    """管理 SSE 连接，支持按 task_id 广播进度事件"""

    def __init__(self):
        # task_id → set of asyncio.Queue
        self._connections: Dict[UUID, set[asyncio.Queue]] = {}

    async def subscribe(self, task_id: UUID) -> asyncio.Queue:
        """订阅某个任务的 SSE 事件流"""
        ...

    def unsubscribe(self, task_id: UUID, queue: asyncio.Queue):
        """取消订阅"""
        ...

    async def broadcast(self, task_id: UUID, event: str, data: dict):
        """向订阅该任务的所有连接广播事件"""
        ...

# 全局单例
sse_manager = SSEManager()
```

---

## 六、前端设计

### 6.1 路由设计

```
/                        首页 (Landing Page)
                          - 产品介绍 + 快速开始 CTA
                          - "创建新分析" 按钮直达 /tasks/new

/tasks                   任务仪表盘（主页面）
                          - 左侧：任务列表（状态筛选 + 搜索 + 分页）
                          - 右侧：快速创建面板（ASIN + CSV 上传 + 开始分析）

/tasks/new               创建新分析任务
                          - 三步向导：选择数据源 → 配置参数 → 确认创建

/tasks/[id]              分析详情页
                          - 运行中：实时进度条 + 当前 Phase 动画
                          - 已完成：嵌入式看板（默认 Tab）
                          - Tab 切换：看板 | 报告 | 评论数据

/tasks/[id]/report       洞察报告全屏
                          - 左侧目录导航（14 章锚点）
                          - 右侧 Markdown 渲染 + Mermaid 图表

/tasks/[id]/reviews      评论数据浏览
                          - 顶部筛选栏（情感、评分、标签维度）
                          - 数据表格 + 分页

/export/[id]             导出下载页
                          - CSV / Markdown / HTML 三按钮下载
```

### 6.2 组件树

```
App
├── Layout
│   ├── Navbar
│   │   ├── Logo (ReviewAnalyzer)
│   │   ├── NavLinks (首页 | 任务 | 关于)
│   │   └── ThemeSelector        // 全局主题切换（影响看板渲染）
│   └── Container (main content)
│
├── Pages
│   ├── HomePage
│   │   ├── HeroSection          // 标题 + 描述 + CTA
│   │   └── FeatureCards         // 22维标签 / 14章报告 / 6套主题
│   │
│   ├── TasksPage (Dashboard)
│   │   ├── TaskListPanel
│   │   │   ├── StatusFilter     // 全部 | 运行中 | 已完成 | 失败
│   │   │   ├── TaskSearchInput
│   │   │   └── TaskCard[]       // 状态图标 + ASIN + 时间 + 进度条
│   │   └── QuickCreatePanel
│   │       ├── AsinInput
│   │       ├── SiteSelect
│   │       ├── CsvUploader      // 拖拽上传 + 预览
│   │       ├── ConfigForm       // max_reviews + template
│   │       └── SubmitButton
│   │
│   ├── TaskDetailPage
│   │   ├── TaskHeader           // ASIN + 状态标签 + 时间
│   │   ├── ProgressSection      // (仅运行中) SSE 实时进度
│   │   │   ├── ProgressBar
│   │   │   └── PhaseIndicator[]
│   │   └── ResultTabs           // (仅已完成)
│   │       ├── DashboardTab
│   │       │   ├── DashboardToolbar   // 主题切换 + 下载 + 全屏
│   │       │   └── DashboardView      // 嵌入式看板
│   │       ├── ReportTab
│   │       │   ├── ReportNav         // 14 章锚点目录
│   │       │   └── MarkdownRenderer  // react-markdown + mermaid
│   │       └── ReviewsTab
│   │           ├── ReviewFilters     // 情感 + 评分 + 标签
│   │           └── ReviewsTable      // 带分页的数据表格
│   │
│   ├── ReportPage
│   │   ├── ReportTOC           // 悬浮的 14 章目录导航
│   │   └── MarkdownRenderer
│   │
│   └── ExportPage
│       └── DownloadButton[]     // CSV / MD / HTML
│
└── Dashboard (themes/)
    ├── ThemeProvider            // CSS 变量注入器
    ├── StatCards                // 指标卡片行
    │   └── StatCard[]           // 单个指标（数值 + 标签 + 变化）
    ├── ChartSection
    │   ├── PieChart             // 情感分布
    │   ├── RadarChart           // 22 维标签
    │   ├── BarChart             // TOP 标签
    │   ├── LineChart            // 评分趋势
    │   └── Histogram            // 信息评分分布
    ├── PersonaSection
    │   └── PersonaCard[]        // 画像卡片（含黄金样本）
    └── TagCloud                 // 关键词词云
```

### 6.3 状态管理设计

#### Zustand Stores (UI 状态)

```typescript
// stores/ui-store.ts
interface UIState {
  // 主题
  currentTheme: ThemeId;              // "premium-gold" | "dark-tech" | ...
  setTheme: (theme: ThemeId) => void;

  // 侧边栏
  sidebarOpen: boolean;
  toggleSidebar: () => void;

  // 通知
  toasts: Toast[];
  addToast: (toast: Toast) => void;
  dismissToast: (id: string) => void;
}

// stores/task-store.ts
interface TaskStoreState {
  // 新建任务草稿（在执行创建前暂存）
  draft: {
    asin: string;
    site: Site;
    source: DataSource;
    uploadId: string | null;
    config: TaskConfig;
  };
  setDraft: (partial: Partial<TaskStoreState['draft']>) => void;
  resetDraft: () => void;

  // 当前正在查看的任务 ID
  activeTaskId: string | null;
  setActiveTask: (id: string | null) => void;
}
```

#### TanStack Query Keys (服务端状态)

```typescript
// hooks/use-tasks.ts

// 任务列表
const TASKS_KEY = ['tasks', { status, offset, limit }] as const;
function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => api.getTasks(filters),
    refetchInterval: (data) =>
      data?.some(t => t.status !== 'done' && t.status !== 'failed') ? 5000 : false,
    // 如果有未完成的任务，每 5 秒轮询
  });
}

// 单个任务
const TASK_KEY = (id: string) => ['tasks', id] as const;
function useTask(id: string) {
  return useQuery({
    queryKey: ['tasks', id],
    queryFn: () => api.getTask(id),
  });
}

// 任务进度（SSE）
function useTaskProgress(taskId: string) {
  // 内部使用 EventSource API 监听 SSE 事件
  // 每次 progress/done/error 事件触发时更新 React Query 缓存
}

// 评论数据
const REVIEWS_KEY = (taskId: string, filters: ReviewFilters) =>
  ['tasks', taskId, 'reviews', filters] as const;

// 用户画像
const PERSONAS_KEY = (taskId: string) =>
  ['tasks', taskId, 'personas'] as const;

// 分析报告
const REPORT_KEY = (taskId: string) =>
  ['tasks', taskId, 'report'] as const;
```

### 6.4 主题系统设计

```typescript
// themes/types.ts
interface ThemeDefinition {
  id: ThemeId;
  name: string;           // 中文名
  description: string;    // 一句话描述
  useCase: string;        // 适用场景
  preview: string;        // 预览图 URL
  tokens: CSSVariables;   // CSS 自定义属性映射
}

type CSSVariables = {
  '--color-bg-primary': string;
  '--color-bg-secondary': string;
  '--color-bg-card': string;
  '--color-text-primary': string;
  '--color-text-secondary': string;
  '--color-accent': string;
  '--color-accent-hover': string;
  '--color-border': string;
  '--color-chart-1': string;
  '--color-chart-2': string;
  '--color-chart-3': string;
  '--color-chart-4': string;
  '--color-chart-5': string;
  '--font-heading': string;
  '--font-body': string;
  '--radius-card': string;
  '--shadow-card': string;
  '--glass-opacity': string;
  '--glass-blur': string;
  // ... 共约 30 个 token
};

// themes/premium-gold/tokens.ts
export const premiumGoldTokens: CSSVariables = {
  '--color-bg-primary': '#0d0d0d',
  '--color-bg-secondary': '#1a1a2e',
  '--color-bg-card': 'rgba(26, 26, 46, 0.6)',
  '--color-text-primary': '#f0e6d3',
  '--color-text-secondary': '#9a8c7a',
  '--color-accent': '#d4af37',
  // ...
};
```

---

## 七、数据流与状态管理

### 7.1 完整分析流程数据流

```
[用户] 输入 ASIN + 上传 CSV / 配置 Sorftime
  │
  ▼
[前端] POST /api/tasks → 创建任务 (status=pending)
  │
  ▼
[后端] Celery Task 入队 → status=fetching
  │
  ├─ SSE: {"event":"progress","data":{"phase":1,...}}
  │
  ▼
[Phase 1: 数据获取]
  review-analyzer-skill/src/data_fetchers/
  ├─ CSV: CsvFetcher → 读取 MinIO 文件 → 标准化评论
  └─ Sorftime: SorftimeFetcher → API 调用 → 标准化评论
  
  → 写入 reviews 表
  → 更新 task.progress = 20
  
  ├─ SSE: {"event":"progress","data":{"phase":2,...}}
  
[Phase 2: AI 打标]
  review-analyzer-skill/src/review_analyzer.py
  → analyze_all() → subprocess 调 claude --print
  → 22 维标签 + sentiment + info_score
  → 写入 tagged_reviews 表
  → 更新 task.progress = 40
  
  ├─ SSE: {"event":"progress","data":{"phase":3,...}}
  
[Phase 3: 用户画像]
  review-analyzer-skill/src/user_persona_analyzer.py
  → analyze_user_personas() → 4 个画像 + 黄金样本
  → 写入 personas 表 + golden_samples 表
  → 更新 task.progress = 60
  
  ├─ SSE: {"event":"progress","data":{"phase":4,...}}
  
[Phase 4: 洞察报告]
  review-analyzer-skill/src/insights_generator.py
  → calculate_stats_summary() + generate_insights()
  → 14 章 MD 报告 + strategic_json
  → 写入 analysis_reports 表
  → 更新 task.progress = 80
  
  ├─ SSE: {"event":"progress","data":{"phase":5,...}}
  
[Phase 5: 输出看板]
  review-analyzer-skill/src/output_manager.py
  → generate_outputs() → HTML + CSV + MD 文件
  → 文件上传至 MinIO
  → 写入 analysis_reports.html_content
  → status=done, progress=100
  
  ├─ SSE: {"event":"done","data":{...}}
  
[前端] SSE done 事件触发 → 自动切换到结果 Tab
  → 加载 GET /api/tasks/{id}/report
  → 渲染 DashboardView (Chart.js 图表 + 画像卡片)
```

### 7.2 前端数据加载策略

| 场景 | 策略 | 实现 |
|------|------|------|
| 任务列表 | 定期轮询 (5s) 当存在未完成任务 | `refetchInterval` 条件触发 |
| 任务进度 | SSE 事件流 | `EventSource` API 原生监听 |
| 已完成看板 | 按需加载 | `staleTime: 5min`，不重复请求 |
| 报告全文 | 懒加载 | 点击 "报告" Tab 时才请求 |
| 评论数据 | 分页 + 筛选 | 每页独立 query key，筛选参数变化时 refetch |
| 文件下载 | Blob 下载 | `fetch → blob → URL.createObjectURL` |

---

## 八、部署架构

### 8.1 Docker Compose 拓扑

```yaml
# docker-compose.yml — 根目录，一键启动全栈

services:
  # ── 反向代理 ──
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend

  # ── 前端服务 ──
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    expose:
      - "3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api

  # ── 后端 API ──
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    expose:
      - "8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://review:review@postgres:5432/reviewanalyzer
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}
      - MINIO_BUCKET=review-analyzer
      - CLI_ENGINE=claude
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      minio:
        condition: service_started

  # ── Celery Worker ──
  celery-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql+asyncpg://review:review@postgres:5432/reviewanalyzer
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}
      - MINIO_BUCKET=review-analyzer
      - CLI_ENGINE=claude
    depends_on:
      - postgres
      - redis
      - minio

  # ── 数据库 ──
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=review
      - POSTGRES_PASSWORD=review
      - POSTGRES_DB=reviewanalyzer
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U review -d reviewanalyzer"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ── 消息队列 / 缓存 ──
  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

  # ── 对象存储 ──
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY:-minioadmin}
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  redisdata:
  miniodata:
```

### 8.2 环境变量清单 (.env)

```bash
# ── 数据库 ──
DATABASE_URL=postgresql+asyncpg://review:review@postgres:5432/reviewanalyzer

# ── Redis ──
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ── MinIO ──
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=review-analyzer

# ── AI 引擎 ──
CLI_ENGINE=claude           # 可选: claude / opencode / none
CLI_TIMEOUT=600             # 单次 CLI 调用超时 (秒)

# ── 分析 ──
MAX_CONCURRENT_AGENTS=4     # 并发批次数
MAX_REVIEWS_DEFAULT=500     # 默认分析条数上限

# ── 应用 ──
APP_ENV=production
LOG_LEVEL=info
```

### 8.3 启动流程

```bash
# 1. 克隆仓库
git clone https://github.com/buluslan/review-analyzer.git
cd review-analyzer

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env（按需修改 MinIO 密钥等）

# 3. 一键启动
docker compose up -d

# 4. 查看服务状态
docker compose ps

# 5. 访问
# 前端:    http://localhost
# 后端 API: http://localhost/api/docs (Swagger)
# MinIO:   http://localhost:9001 (Console)
```

---

## 九、非功能需求

### 9.1 性能

| 指标 | 目标 | 测量方法 |
|------|------|---------|
| 单次分析 (500 条评论) | < 15 min | Celery task duration |
| API 响应时间 (P99) | < 500ms | structlog request duration |
| SSE 进度推送延迟 | < 2s | 进度事件时间戳间隔 |
| 首页 FCP (First Contentful Paint) | < 1.5s | Lighthouse |
| 看板 LCP (Largest Contentful Paint) | < 3s | Lighthouse |
| 数据库查询 (100 条分页) | < 50ms | SQLAlchemy query log |

### 9.2 可用性

- Docker Compose 一键启动，所有服务自动编排
- PostgreSQL 健康检查确保依赖启动顺序
- 分析任务失败自动重试 3 次，可达状态标记为 `failed`
- Celery worker 崩溃后 Docker 自动重启（`restart: unless-stopped`）
- MinIO / Redis 数据卷持久化，`docker compose down` 后数据不丢失

### 9.3 安全性

| 措施 | 实现 |
|------|------|
| SQL 注入防护 | SQLAlchemy ORM 参数化查询 |
| 文件上传限制 | 50MB 上限 + 仅允许 `.csv` 扩展名 |
| 敏感信息 | `.env` 管理，不写入代码；Sorftime API Key 仅内存传递 |
| CORS | 仅允许 `localhost` 和配置的前端域名 |
| 请求大小限制 | FastAPI `maximum_request_size=50MB` |
| 容器网络隔离 | Docker Compose 内部网络，仅 nginx 暴露 80 端口 |

### 9.4 可维护性

| 措施 | 实现 |
|------|------|
| 代码规范 | Python: ruff + mypy strict; TypeScript: Biome + strict mode |
| API 文档 | FastAPI 自动生成 Swagger UI (`/docs`) |
| 数据库迁移 | Alembic 版本化管理 |
| 结构化日志 | structlog JSON 格式，`docker logs` 直接解析 |
| 模块化 | 每文件 ≤ 500 行；前端组件树分层；后端三层架构（api → service → model） |
| 分析引擎独立 | `review-analyzer-skill/` 无外部依赖，可脱离 Web 层独立升级 |

---

## 十、测试策略

### 10.1 测试金字塔

```
        ╱  E2E ╲              Playwright (关键路径)
       ╱        ╲
      ╱ 集成测试  ╲            httpx + pytest-asyncio (API 全链路)
     ╱            ╲
    ╱   单元测试    ╲           pytest + Vitest (核心逻辑)
   ╱────────────────╲
```

### 10.2 后端测试

| 层 | 工具 | 策略 | 覆盖目标 |
|-----|------|------|---------|
| **单元测试** | pytest | Model 方法、工具函数、ASIN 校验、Pydantic schema 验证 | ≥ 90% |
| **服务测试** | pytest + pytest-asyncio | Service 层业务逻辑（mock DB 操作） | ≥ 85% |
| **API 测试** | httpx + TestClient (async) | 完整请求-响应链路，含数据库事务回滚 | ≥ 80% |
| **Celery 测试** | pytest + celery_worker fixture | 任务入队 → 执行 → 状态更新 | ≥ 70% |
| **分析引擎** | pytest（mock CLI subprocess） | 各 Phase 模块输入/输出正确性 | ≥ 90% |

**Mock 策略**：
- Claude Code CLI `subprocess.run()` → mock，不实际调用
- MinIO 客户端 → mock（本地文件系统代替）
- Sorftime API → mock 固定响应

### 10.3 前端测试

| 层 | 工具 | 策略 | 覆盖目标 |
|-----|------|------|---------|
| **单元测试** | Vitest + React Testing Library | 组件渲染、Hook 逻辑、Zustand store | ≥ 80% |
| **集成测试** | Vitest + Mock Service Worker (MSW) | 组件 + API 交互全流程 | ≥ 70% |
| **E2E** | Playwright | 关键用户流程：创建任务 → 等待完成 → 查看看板 | 核心路径 100% |

**E2E 核心场景**：
1. 上传 CSV → 创建任务 → 进度实时更新 → 看板正确渲染
2. 任务列表筛选 → 点击历史任务 → 离线查看报告
3. 文件下载 → CSV/MD/HTML 完整性
4. 主题切换 → 6 套主题均可正常渲染

### 10.4 CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: ruff check backend/
      - run: mypy backend/ --strict

  backend-test:
    needs: backend-lint
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: test }
    runs-on: ubuntu-latest
    steps:
      - run: pytest backend/ -v --cov --cov-report=xml

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - run: pnpm install
      - run: pnpm biome check frontend/
      - run: pnpm tsc --noEmit

  frontend-test:
    needs: frontend-lint
    runs-on: ubuntu-latest
    steps:
      - run: pnpm vitest run --coverage

  # E2E 在 main 合并后运行（耗时较长）
  e2e:
    if: github.ref == 'refs/heads/main'
    needs: [backend-test, frontend-test]
    runs-on: ubuntu-latest
    steps:
      - run: docker compose up -d
      - run: pnpm playwright test
```

---

## 十一、里程碑规划

### Phase 2: React 全栈产品化（目标 4-6 周）

| Step | 内容 | 工期 | 产物 |
|------|------|------|------|
| **1. 项目骨架** | `backend/` + `frontend/` 目录创建，FastAPI 入口 + Next.js 入口 | 2-3 天 | 可运行的空项目，health check 通过 |
| **2. 数据库** | PostgreSQL 建表 + Alembic 迁移 + SQLAlchemy 模型 | 2-3 天 | 迁移脚本 + 模型文件 |
| **3. 任务 API** | CRUD + Celery worker + SSE 进度推送 | 5-7 天 | `/api/tasks` 全部端点可用 |
| **4. 分析 Pipeline** | Celery task 内调用 review-analyzer-skill 5 Phase 流程 | 3-4 天 | 端到端分析可执行 |
| **5. 前端页面** | 6 个页面 React 组件开发 | 5-7 天 | 全部路由页面可用 |
| **6. 主题组件** | 6 套主题设计 tokens + Dashboard 可视化组件 | 5-7 天 | 主题切换 + Chart.js 图表 |
| **7. 文件存储** | MinIO 集成 + 上传/下载 API | 2-3 天 | 文件上传下载流程 |
| **8. 导出功能** | CSV / MD / HTML 导出 + 下载按钮 | 1-2 天 | 三个导出端点 |
| **9. Docker** | Dockerfile × 4 + docker-compose.yml | 3-4 天 | 一键部署 |
| **10. 测试** | pytest + Vitest + Playwright | 3-4 天 | CI 全绿 |
| **11. 文档发布** | README + Swagger + CHANGELOG + v2.0.0 Release | 2-3 天 | GitHub Release |

**总工期估算：6-8 周**（1 人全职），关键路径为 Step 3-6。

---

## 十二、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Claude Code CLI 不稳定/超时 | 中 | 分析失败 | 内置重试（3 次）+ 超时配置（600s）+ 失败任务可重试 |
| 分析耗时长（500 条 >15min） | 中 | 用户体验差 | 异步 Celery + SSE 实时推送 + 进度可视化；优化并发数 |
| Amazon 数据获取依赖第三方 | 低 | 数据源不可用 | CSV 上传始终作为兜底方案 |
| 6 套主题 React 重写工作量大 | 高 | 延期 | 提炼 CSS 变量体系（一套组件多套皮肤）；优先完成 2 套核心主题 |
| Celery + Redis 增加部署复杂度 | 低 | 自托管用户上手困难 | Docker Compose 封装 + README 详细步骤 |
| 单用户版本后续扩展多用户 | 中 | 重构成本 | 数据库设计已预留 `users` 表位置；API 中间件接口已规划 |

---

## 十三、附录

### A. 项目结构总览

```
ReviewAnalyzer/
├── review-analyzer-skill/          # 分析引擎（▲ 复用，不改动）
│   ├── main.py                     # CLI 入口
│   ├── SKILL.md
│   ├── src/
│   │   ├── config.py
│   │   ├── data_fetchers/          # CSV + Sorftime 数据接入
│   │   ├── review_analyzer.py      # Phase 2: AI 打标
│   │   ├── user_persona_analyzer.py# Phase 3: 用户画像
│   │   ├── insights_generator.py   # Phase 4: 洞察报告
│   │   ├── output_manager.py       # Phase 5: 输出管理
│   │   ├── template_engine.py      # Jinja2 模板引擎
│   │   ├── chart_engine.py         # Chart.js 配置
│   │   ├── prompts/                # Prompt 模板
│   │   └── templates/              # 6 套 HTML 主题模板
│   └── references/                 # 标签体系 + CSV 格式
│
├── backend/                        # ▲ 新建: FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                   # 配置 + 数据库引擎
│   │   ├── api/                    # 路由层 (tasks, reviews, reports, export, upload)
│   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── schemas/                # Pydantic 请求/响应 schema
│   │   ├── services/               # 业务逻辑层
│   │   └── tasks/                  # Celery 任务定义
│   ├── alembic/                    # 数据库迁移
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # ▲ 新建: Next.js 前端
│   ├── src/
│   │   ├── app/                    # Next.js App Router 页面
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui 基础组件
│   │   │   ├── dashboard/          # 看板组件 (StatCard, Charts...)
│   │   │   ├── tasks/              # 任务相关组件
│   │   │   └── themes/             # 6 套主题定义
│   │   ├── hooks/                  # 自定义 Hook (useTask, useSSE...)
│   │   ├── stores/                 # Zustand stores
│   │   ├── lib/                    # API client + 工具函数
│   │   └── styles/                 # 全局样式 + Tailwind config
│   ├── tests/
│   ├── e2e/                        # Playwright 测试
│   ├── package.json
│   ├── tsconfig.json
│   ├── biome.json
│   └── Dockerfile
│
├── docker-compose.yml              # 一键编排
├── .env.example                    # 环境变量模板
├── nginx.conf                      # 反向代理配置
├── CLAUDE.md                       # 项目规则
├── README.md
└── .memory-bank/                   # 项目文档
    ├── PRD.md                      # ← 本文件
    ├── architecture.md
    ├── tech_stack.md
    ├── implementation_plan_phase2.md
    └── progress.md
```

### B. 竞品对比

| 产品 | 定位 | 月费 | ReviewAnalyzer 差异化 |
|------|------|------|----------------------|
| Jungle Scout | 全功能卖家工具 | $49+ | 聚焦评论深度分析，非全能工具 |
| Helium 10 | 全功能卖家工具 | $39+ | 14 章 AI 洞察报告，维度更深 |
| AMZScout | 选品工具 | $44+ | 开源免费，数据不出服务器 |
| **ReviewAnalyzer** | **评论深度分析** | **免费** | **22维标签 + 画像 + 6套看板 + 零AI成本** |

### C. 术语表

| 术语 | 含义 |
|------|------|
| ASIN | Amazon Standard Identification Number，亚马逊标准识别码（10 位字母数字） |
| 22 维标签 | AI 打标的 22 个维度（人群_性别、使用_场景、产品_质量...），定义在 `tag_system.yaml` |
| 14 章报告 | AI 生成的 14 个章节洞察报告（市场定位、用户画像、产品优劣势...） |
| Phase 1-5 | 分析流水线的 5 个阶段（数据获取 → 打标 → 画像 → 报告 → 输出） |
| 黄金样本 | 每个用户画像最具代表性的 3 条正面 + 3 条负面评论 |
| 画像 | 基于「使用场景 × 性别」交叉的典型用户群体（最多 4 个） |
| SSE | Server-Sent Events，服务端向浏览器单向推送事件流 |
| Celery | Python 分布式任务队列，用于异步执行耗时的分析任务 |
| MinIO | 兼容 AWS S3 API 的开源对象存储服务 |

### D. 参考资源

- [Claude Code CLI 文档](https://docs.anthropic.com/en/docs/claude-code)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Next.js 文档](https://nextjs.org/docs)
- [SQLAlchemy 2.0 异步指南](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Celery 最佳实践](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Chart.js 文档](https://www.chartjs.org/docs/latest/)
- [Tailwind CSS v4](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
