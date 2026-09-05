# CLAUDE.md — ReviewAnalyzer 项目规则

> 本文件由 Claude Code 在每次会话启动时自动加载。
> 所有规则适用于本项目的任何 AI 编码助手（Claude Code / Codex CLI / Cursor 等）。

---

## Always Rules（始终生效）

```
# ═══════════════════════════════════════════════════════════════
# 文档驱动（最高优先级 — 写代码前必须先读文档）
# ═══════════════════════════════════════════════════════════════
# ALWAYS: 写任何代码前，先读取 .memory-bank/architecture.md（包含完整数据库 schema + 模块职责 + 数据流）
# ALWAYS: 写任何代码前，先读取 .memory-bank/PRD.md（包含 API Schema + 组件树 + 状态管理设计）
# ALWAYS: 添加重大功能或完成里程碑后，更新 .memory-bank/architecture.md

# ═══════════════════════════════════════════════════════════════
# 实施流程（禁止跳过）
# ═══════════════════════════════════════════════════════════════
# ALWAYS: 按 .memory-bank/implementation_plan.md 的 Step 顺序执行，禁止跳过或并行执行多个 Step
# ALWAYS: 每完成一个 Step 后，必须按以下顺序操作：
#   ① 自动化验证 — 执行该 Step 中「验证方式」表格的所有验证项 → 全部通过
#   ② 提示用户手动验证 — 用户在浏览器/终端中确认结果
#   ③ 用户确认通过后 — 更新 .memory-bank/progress.md（该 Step 状态改为 ✅，填写完成日期）
#   ④ 用户执行 git add -A，AI 提供 git commit -m 提交说明，用户执行提交
#   ⑤ 然后才进入下一个 Step
# ALWAYS: 任何 Step 验证失败时，先修复问题再继续，禁止带着已知问题进入下一步

# ═══════════════════════════════════════════════════════════════
# 模块化（最高优先级 — 可维护性的基石）
# ═══════════════════════════════════════════════════════════════
# ALWAYS: 每个功能模块独立一个文件，严格禁止单文件超过 500 行
# ALWAYS: 超过 500 行的文件必须拆分；拆到每个文件职责可用一句话描述清楚
# ALWAYS: 新建文件前，先判断其职责是否可归入现有模块；能复用的绝不新建
# ALWAYS: 禁止创建 utils.py / helpers.py / common.py / misc.py 等"万能杂物间"文件
# ALWAYS: 后端遵循三层架构：api/ 只做路由+校验 → services/ 做业务逻辑 → models/ 做数据定义
#         禁止在 api/ 中写业务逻辑，禁止在 services/ 中直接操作 HTTP 请求/响应对象
# ALWAYS: 前端遵循三层拆分：pages/ 只做页面组装 → components/features/ 做功能区块 → components/ui/ 做原子组件
#         禁止在 page.tsx 中写超过 50 行的业务逻辑

# ═══════════════════════════════════════════════════════════════
# 代码质量
# ═══════════════════════════════════════════════════════════════
# ALWAYS: 新增功能必须写测试，覆盖率目标 ≥ 80%
# ALWAYS: 后端代码遵循 Python 3.13+ 语法，使用 ruff 格式化和 mypy --strict 类型检查
# ALWAYS: 前端代码使用 TypeScript strict mode，Biome 格式化和 lint
# ALWAYS: 所有 import 必须显式写出，禁止 import * 和未声明的隐式依赖
# ALWAYS: API 请求/响应必须用 Pydantic v2 (后端) / Zod (前端) 校验，前后端校验规则必须一致
# ALWAYS: 敏感信息（API Key、密码、密钥）只能出现在 .env 中，禁止硬编码到任何源码文件
# ALWAYS: 调用 Claude CLI 必须通过 config.build_cli_cmd() 统一入口，禁止裸写 subprocess.run(["claude", ...])
```

---

## 项目概述

**ReviewAnalyzer** 是面向跨境电商运营人员的 Amazon 评论深度分析平台。

- **定位**：MIT 开源，Docker 自托管，免费
- **AI 引擎**：Claude Code CLI subprocess 调用（`config.build_cli_cmd()`），零 API Key 成本
- **五阶段流水线**：数据获取 → AI 打标 (22维) → 用户画像 → 14章洞察报告 → 可视化看板
- **当前阶段**：Phase 2 全栈版开发中（12 个 Step，详见 implementation_plan.md）
- **前置状态**：
  - `review-analyzer-skill/` — 分析引擎，已完成，**只读不改**
  - `backend/` — 待构建 (FastAPI + Celery + PostgreSQL)
  - `frontend/` — 待构建 (Next.js 15 + React 19 + TypeScript)

## 文档导航

> 写任何代码前，按以下顺序阅读：

| 优先级 | 文档 | 用途 | 何时读 |
|--------|------|------|--------|
| **1** | `.memory-bank/architecture.md` | 架构全景 + 模块职责 + 数据流 + DB schema | **每次写代码前** |
| **2** | `.memory-bank/PRD.md` | 功能需求 + API Schema + 组件树 + 状态管理 | **每次写代码前** |
| 3 | `.memory-bank/tech_stack.md` | 技术选型 + ADR 决策记录 + 依赖清单 | 引入新技术/不确定选型时 |
| 4 | `.memory-bank/implementation_plan.md` | 12 Step 详细操作指令 + 验证方式 | 开始每个 Step 前 |
| 5 | `.memory-bank/progress.md` | 当前进度 + 下一步 | 每次会话开始 |

## 技术栈速查

| 层 | 技术 | 版本 |
|----|------|------|
| **前端框架** | Next.js (App Router, SPA) | 15 |
| **UI 库** | React + TypeScript strict | 19 / 5.7 |
| **CSS** | Tailwind CSS + shadcn/ui | v4 |
| **状态管理** | Zustand (UI) + TanStack Query (服务端) | v5 |
| **图表** | Chart.js + react-chartjs-2 | 4 |
| **后端框架** | FastAPI + Uvicorn + Gunicorn | ≥0.115 |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | ≥2.0.36 |
| **校验** | Pydantic v2 / Zod | ≥2.10 |
| **任务队列** | Celery + Redis 7 | ≥5.4 |
| **数据库** | PostgreSQL 16 | — |
| **文件存储** | MinIO (S3 兼容) | latest |
| **AI 引擎** | Claude Code CLI (subprocess) | — |
| **包管理** | uv (Python) + pnpm (Node.js) | — |
| **代码质量** | ruff + mypy strict / Biome | — |
| **测试** | pytest + pytest-asyncio / Vitest + Playwright | — |
| **部署** | Docker Compose (7 服务) | — |

详细选型理由及 ADR 见 `.memory-bank/tech_stack.md`。

## 项目结构

```
ReviewAnalyzer/
├── review-analyzer-skill/      # ▲ 分析引擎（不改动，只 import 复用）
│   ├── main.py                 # CLI 入口（5 Phase 流程）
│   ├── SKILL.md                # Claude Code Skill 定义
│   └── src/
│       ├── config.py           # 全局配置（CLI 引擎、路径、并发等）
│       ├── data_fetchers/      # 数据接入层（CSV + Sorftime）
│       ├── review_analyzer.py  # Phase 2: AI 打标引擎（ThreadPoolExecutor 并发）
│       ├── user_persona_analyzer.py  # Phase 3: 用户画像识别
│       ├── insights_generator.py     # Phase 4: 14章洞察报告生成
│       ├── output_manager.py         # Phase 5: 统一输出管理
│       ├── template_engine.py        # V2 Jinja2 模板引擎（6 套主题 HTML）
│       ├── chart_engine.py           # Chart.js 图表配置
│       ├── data_loader.py            # CSV 数据加载（列名模糊匹配）
│       ├── prompts/                  # Prompt 模板管理
│       └── templates/                # 6 套 HTML 可视化主题
│
├── backend/                    # ▲ 构建中: FastAPI 后端
│   ├── app/
│   │   ├── main.py             # FastAPI 入口 + CORS + 生命周期
│   │   ├── core/               # config + database (AsyncEngine)
│   │   ├── api/                # 路由层（仅路由+校验，禁止业务逻辑）
│   │   ├── models/             # SQLAlchemy ORM（7 张表）
│   │   ├── schemas/            # Pydantic v2 请求/响应
│   │   ├── services/           # 业务逻辑层（task/pipeline/storage/sse）
│   │   ├── tasks/              # Celery 任务（celery_app + analysis_task）
│   │   └── utils/              # 纯工具函数（如 ASIN 校验）
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # pytest
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/                   # ▲ 构建中: Next.js 前端
│   ├── src/
│   │   ├── app/                # 7 个路由页面（App Router）
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui 原子组件
│   │   │   ├── layout/         # Navbar + Container
│   │   │   ├── tasks/          # 任务相关功能组件
│   │   │   ├── dashboard/      # 看板可视化组件
│   │   │   └── themes/         # 6 套主题定义 + ThemeProvider
│   │   ├── hooks/              # 自定义 Hook（useTasks, useSSE...）
│   │   ├── stores/             # Zustand（ui-store, task-draft-store）
│   │   ├── lib/                # API client + Zod validators + utils
│   │   ├── styles/             # Tailwind + 主题 CSS 变量
│   │   └── types/              # 共享 TypeScript 类型
│   ├── tests/                  # Vitest
│   ├── e2e/                    # Playwright
│   ├── package.json
│   ├── tsconfig.json
│   ├── biome.json
│   └── Dockerfile
│
├── .memory-bank/               # 项目文档（AI 编码引导）
│   ├── PRD.md                  # 产品需求（API + 组件 + 状态管理）
│   ├── tech_stack.md           # 技术选型（ADR 决策记录）
│   ├── architecture.md         # 架构文档（DB schema + 模块 + 数据流）
│   ├── implementation_plan.md  # 实施计划（12 Step 操作指令）
│   └── progress.md             # 进度跟踪
│
├── docker-compose.yml          # 7 服务编排（Step 11 创建）
├── nginx.conf                  # 反向代理（Step 11 创建）
├── .env.example                # 环境变量模板
├── .gitignore
└── README.md
```

## 编码规范

### Python（后端 + Celery Worker）

```python
# ── 文件头：必须有 docstring 说明模块职责 ──
"""
模块名称 — 一句话描述

详细说明（可选）
"""

# ── Imports 分四组，空行分隔 ──
# 1. 标准库
import os
from pathlib import Path

# 2. 第三方库
from fastapi import APIRouter, Depends, HTTPException
import structlog

# 3. 项目内部模块
from app.core.config import settings
from app.models.task import Task

# 4. 类型注解
from typing import Optional
from uuid import UUID

# ── 类型注解：所有公开函数必须有 ──
async def create_task(data: TaskCreate, db: AsyncSession) -> TaskResponse:
    """创建分析任务，校验 ASIN 格式和数据源配置。返回 TaskResponse。"""
    ...

# ── 配置：统一使用 app.core.config 的 settings 实例 ──
# ✅ 正确
from app.core.config import settings
api_key = settings.SORFTIME_API_KEY

# ❌ 错误 — 禁止各自读环境变量
api_key = os.getenv("SORFTIME_API_KEY")

# ── CLI 调用：必须通过统一入口 ──
# ✅ 正确
from src.config import config
cmd = config.build_cli_cmd(prompt)
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

# ❌ 错误 — 禁止裸写 subprocess
subprocess.run(["claude", "--print", prompt])

# ── 数据库操作：必须使用依赖注入的 session ──
# ✅ 正确
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)) -> TaskResponse:
    ...

# ❌ 错误 — 禁止在模块顶层创建 session 或使用同步 session
db = SessionLocal()  # 禁止
```

**三层架构强制规则**：

```
api/     → 只做：路由定义 + 参数校验 (Depends) + 调用 service + 返回响应
           禁止：SQL 查询、文件 I/O、业务判断、直接操作 MinIO/Redis
           ─────────────────────────────────────────────
services/ → 只做：业务逻辑编排 + 数据库 CRUD + 外部服务调用
           禁止：访问 Request/Response 对象、设置 HTTP 状态码
           ─────────────────────────────────────────────
models/  → 只做：表结构定义 + 关系映射 + 简单属性方法
           禁止：业务逻辑、API 调用、文件操作
```

### TypeScript / React（前端）

```typescript
// ── 文件头：组件必须有 JSDoc ──
/** 任务列表组件 — 展示用户的所有分析任务，支持状态筛选和分页 */
export function TaskList({ filters }: TaskListProps) { ... }

// ── 类型优先：禁止 any ──
// ✅ 正确：unknown + type guard
function process(data: unknown): TaskResponse {
  if (!isTaskResponse(data)) throw new Error("Invalid data");
  return data;
}

// ❌ 错误：any 逃逸类型检查
function process(data: any): any { ... }

// ── API 响应校验：所有 API 返回必须用 Zod 校验 ──
const TaskResponseSchema = z.object({
  id: z.string().uuid(),
  asin: z.string().length(10),
  status: z.enum(["pending", "fetching", "tagging", "analyzing", "rendering", "done", "failed"]),
  // ...
});

// ── 组件拆分：页面 → 功能区块 → UI 原子，每层独立文件 ──
// ✅ 正确
// pages/tasks/[id]/page.tsx → components/tasks/TaskProgress.tsx → components/ui/ProgressBar.tsx

// ❌ 错误 — 所有逻辑塞在一个 page.tsx 中（超过 50 行业务逻辑必须拆分）
```

**前端三层拆分强制规则**：

```
app/ (pages)      → 只做：页面组装 + 布局 + SEO metadata
                    禁止：超过 50 行的业务逻辑、直接 fetch 调用
                    ─────────────────────────────────────────
components/       → 只做：功能区块组件（容器组件 + 展示组件）
  ui/                 原子组件（button, card, dialog...）
  tasks/              任务功能组件（TaskCard, CreateForm...）
  dashboard/          看板组件（StatCards, PieChart...）
  themes/             主题组件（ThemeProvider, theme tokens）
                    ─────────────────────────────────────────
hooks/            → 只做：数据获取 + 副作用封装（TanStack Query + SSE）
stores/           → 只做：客户端 UI 状态（Zustand）
lib/              → 只做：纯函数工具（API client, validators, formatters）
```

## 模块化规则（最高优先级）

> AI 编码助手最大的坏习惯就是把所有逻辑塞进一个巨型文件。以下规则是项目可维护性的基石，**违反任何一条都必须重写**。

### 硬约束

1. **文件大小硬上限**：**500 行**。超过即拆分，无例外，无借口。
   - 检查方式：`wc -l <file>`，超过 490 行时就要规划拆分

2. **禁止万能杂物间文件**：以下文件名**在任何目录下都不允许创建**：
   - `utils.py` / `helpers.py` / `common.py` / `misc.py` / `shared.py`
   - `utils.ts` / `helpers.ts` / `common.ts` / `misc.ts`
   - 正确做法：按功能命名 → `asin_utils.py`、`date_formatters.ts`、`csv_parser.py`

3. **新建文件前自检三问**：
   - 这个功能是否属于某个已有模块？→ 归入已有模块
   - 这个文件未来会不会超过 500 行？→ 现在就拆
   - 这个文件能否用一句话描述清楚职责？→ 不能就别建

### 模块拆分决策树

```
需要写新功能
  │
  ├─ 是否可归入现有模块？
  │   └─ YES → 修改现有文件（确认不超 500 行）
  │
  └─ NO → 新建文件
        │
        ├─ 文件职责能否一句话说清？
        │   └─ NO → 再拆，拆到能说清为止
        │
        └─ YES → 创建，命名遵循功能+类型模式
              ├─ Python: {功能}_{角色}.py  (例: task_service.py, asin_utils.py)
              └─ TS:     {功能}-{角色}.tsx (例: task-card.tsx, use-sse.ts)
```

### 反模式速查

| 反模式 | 症状 | 正确做法 |
|--------|------|---------|
| **上帝文件** | 单个文件 800+ 行，包含路由+业务+数据库操作 | 按 api → service → model 三层拆分 |
| **杂物间** | `utils.py` 里塞了 20 个互不相关的函数 | 按功能分文件：`asin_utils.py`, `date_utils.py`, `csv_utils.py` |
| **页面巨石** | `page.tsx` 里写了 API 调用 + 状态管理 + UI + 业务逻辑 | 抽 hooks + components + lib |
| **重复造轮子** | 在 backend/services/ 中重新实现 CSV 解析 | 直接 import review-analyzer-skill 的 data_loader |
| **裸写 subprocess** | `subprocess.run(["claude", "--print", prompt])` | 必须用 `config.build_cli_cmd(prompt)` |

## 分析流水线约定

```
Phase 1: data_fetchers/          → 标准化评论列表 list[dict]
Phase 2: review_analyzer.py      → 22维标签 + info_score + sentiment
Phase 3: user_persona_analyzer   → 画像列表 (≤4个) + 黄金样本 (每画像3正+3负)
Phase 4: insights_generator.py   → MD洞察报告 + strategic_json + stats
Phase 5: output_manager.py       → MD + HTML看板 + CSV (+ 飞书同步)
```

- Phase 间通过**明确的数据结构**在内存中传递，不通过文件系统（Phase 5 输出除外）
- Phase 2 的 AI 调用必须通过 `config.build_cli_cmd()` 统一入口
- Celery Worker 中运行的 Phase 进度通过 Redis Pub/Sub → SSE Manager 广播到前端
- `review-analyzer-skill/src/` 中的模块**零改动复用**，backend/ 只负责编排和持久化

## 测试规范

- 后端测试文件放在 `backend/tests/`，命名 `test_<模块名>.py`
- 前端测试文件放在 `frontend/tests/`，命名 `*.test.ts`
- CLI 调用层（subprocess.run）必须 mock，不实际调用 claude
- 关键模块（review_analyzer / persona / insights）覆盖率要求 ≥ 90%
- 整体覆盖率目标 ≥ 80%
- 每个 Step 完成后必须运行该 Step 相关的测试套件，确认全部通过

### 后端 API 测试强制规则

```
# 每个 API 端点都必须有走完整 HTTP 管道的集成测试 — 禁止只用 sync db 测数据层。
# 只测数据层会漏掉真实 bug：Pydantic schema 字段缺失、Content-Disposition 编码错误、
# Response/StreamingResponse 生命周期冲突等。

# ✅ 正确 — HTTP 集成测试（走 TestClient + 真实 async FastAPI）
def test_report_200(self, db, client):
    task = _setup_complete(db)
    make_data_visible(db)          # ← 将 sync fixture 的数据提交到 PG
    resp = client.get(f"/api/tasks/{task.id}/report")
    assert resp.status_code == 200
    assert "insights_md" in resp.json()
    assert "template_name" in resp.json()

# ❌ 错误 — 纯数据层测试（绕过 FastAPI，只测 SQLAlchemy 查询）
def test_report_query(self, db):
    report = db.execute(select(AnalysisReport).where(...)).scalar_one()
    assert report.insights_md is not None  # 骗自己：API 层可能 schema 字段名不匹配

# 覆盖率要求：每个 API 端点 ≥ 1 个 200 测试 + ≥ 1 个错误场景测试（404/422）
```

**conftest 提供的测试基础设施（已就绪）**：

| 工具 | 用途 |
|------|------|
| `client` fixture | FastAPI TestClient，发送真实 HTTP 请求 |
| `db` fixture | 同步 Session，在测试中创建数据 |
| `make_data_visible(db)` | 将 sync 事务提交到 PG，使 async `get_db()` 可见 |
| `_patch_async_engine` | session 级 autouse，NullPool 防 event loop 泄漏 |

## 常见陷阱

| # | 陷阱 | 后果 | 规避 |
|---|------|------|------|
| 1 | 修改 prompt 模板后忘记同步更新 SKILL.md 和 PRD.md 的描述 | prompt 与文档不一致 | 改 prompt 时同步更新文档 |
| 2 | 在 `api/` 路由中写数据库查询 | 三层架构崩坏，api 文件膨胀 | 数据库操作必须在 services/ 中 |
| 3 | 硬编码 claude 路径或裸写 subprocess | CLI 引擎不可切换 | 必须用 `config.build_cli_cmd()` |
| 4 | 创建 `utils.py` 往里塞各种函数 | 杂物间文件膨胀到 1000+ 行 | 按功能命名分文件 |
| 5 | 前端 page.tsx 中直接 fetch | 无缓存、无错误处理、无类型校验 | 用 TanStack Query hooks + Zod |
| 6 | 忘记更新 progress.md | 进度跟踪失效，不知道做到哪了 | 每完成一个 Step 立即更新 |
| 7 | 跳过 Step 验证直接进入下一步 | 带着 bug 堆叠，后期调试困难 | 严格按 ①②③④ 流程 |
| 8 | 在 Celery task 中直接操作 FastAPI Request 对象 | Worker 进程中无 Request 上下文 | Celery task 只收 UUID + dict 参数 |
| 9 | API 测试只用 sync db 测数据层，不走 HTTP | 漏掉 schema 字段缺失、header 编码、Response 生命周期等 bug | 必须用 TestClient + make_data_visible() 走完整 HTTP 管道 |

## 当前状态与下一步

- **当前 Step**：Step 11 — Docker Compose 完成，下一步 Step 12（测试+文档）
- **进度**：11/12 = 92%
- **详见**：`.memory-bank/implementation_plan.md` Step 12
