# ReviewAnalyzer — 技术选型文档

> 版本: v1.0 | 日期: 2026-07-03 | 状态: 已确定
>
> 本文档记录项目全链路技术选型及决策理由，与 [PRD.md](PRD.md) 三、技术架构 互补阅读。
> 架构图和里程碑规划见 PRD；本文档聚焦"用什么、为什么、怎么用"。

---

## 一、总览

```
┌────────────────────────────────────────────────────────────┐
│                      Frontend (Phase 2)                     │
│  Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui         │
│  Zustand (状态) + TanStack Query (数据获取)                   │
│  Chart.js (图表) + React Hook Form (表单)                    │
│  Vitest + React Testing Library + Playwright (测试)          │
│  Biome (lint/format)                                        │
└──────────────────────┬─────────────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────▼─────────────────────────────────────┐
│                    Backend (Phase 2)                         │
│  Python 3.13 + FastAPI + Celery + SQLAlchemy 2.0            │
│  Pydantic v2 (校验) + Alembic (迁移)                         │
│  structlog (日志) + pytest (测试)                             │
│  ruff (lint/format) + mypy (类型检查)                        │
└──────────────────────┬─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                     Data Layer                               │
│  PostgreSQL 16 (主库) + Redis 7 (缓存/队列)                   │
│  MinIO (文件/导出物) + SQLite (Phase 1 过渡)                  │
└─────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────┐
│                AI Engine（复用现有模块）                       │
│  Claude Code CLI (subprocess, Phase 1 直调)                  │
│  → Anthropic API 直调 (Phase 2 评估迁移)                      │
└────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────┐
│                    DevOps                                    │
│  Docker Compose (自托管部署) + GitHub Actions (CI/CD)         │
│  GitHub Container Registry (镜像发布)                         │
└────────────────────────────────────────────────────────────┘
```

---

## 二、前端 (Phase 2: React 全栈期)

### 2.1 核心框架

| 技术 | 选型 | 理由 |
|------|------|------|
| **框架** | Next.js 15 (App Router) | SPA 模式为主，按需 SSR（分享链接的 SEO）；Vercel 生态成熟，Docker 自托管也支持良好 |
| **语言** | TypeScript (strict) | 类型安全，IDE 智能提示，重构信心保障 |
| **CSS** | Tailwind CSS v4 | 原子化 CSS，与 shadcn/ui 深度绑定，6 套主题可抽象为 design tokens |
| **组件库** | shadcn/ui | 无依赖、可定制、Tree-shakable；基于 Radix UI 的无障碍组件，复制源码到项目中而非 npm 安装 |

### 2.2 状态管理与数据获取

| 技术 | 选型 | 理由 |
|------|------|------|
| **客户端状态** | Zustand | ~1KB，API 极简，零 boilerplate。管理：用户登录态、任务进度、主题切换、UI 临时状态 |
| **服务端数据** | TanStack Query (React Query v5) | 自动缓存/失效/重试，完美处理任务状态轮询、分析列表分页、SSE 实时更新 |
| **URL 状态** | Next.js useSearchParams | 搜索/筛选参数保持 URL 可分享 |

### 2.3 图表与可视化

| 技术 | 选型 | 理由 |
|------|------|------|
| **图表库** | Chart.js 4 + react-chartjs-2 | 与现有 CLI 版 6 套模板的 Chart.js 配置**完全复用**，零迁移成本 |
| **Markdown 渲染** | react-markdown + remark-gfm + rehype-highlight | 渲染 14 章洞察报告，支持 GFM 表格、Mermaid 代码块高亮 |
| **Mermaid 图表** | mermaid.js (客户端渲染) | 报告中的流程图、象限图在浏览器端实时渲染 |

### 2.4 表单与验证

| 技术 | 选型 | 理由 |
|------|------|------|
| **表单** | React Hook Form | 性能最优（非受控组件），与 Zod 深度集成 |
| **校验** | Zod | 前后端共享 schema（TypeScript ↔ Python Pydantic 对应），类型自动推导 |

### 2.5 测试

| 技术 | 用途 | 理由 |
|------|------|------|
| **单元测试** | Vitest + React Testing Library | Vite 原生速度，与 Jest API 兼容，社区标准 |
| **E2E** | Playwright | 多浏览器支持，Docker 中可无头运行，GitHub Actions 集成简单 |
| **覆盖率目标** | ≥ 80% | 全面策略（用户选择），关键路径 100% |

### 2.6 代码质量

| 技术 | 用途 |
|------|------|
| **Biome** | Lint + Format（替代 ESLint + Prettier），单一二进制文件，速度快 10x+ |
| **TypeScript** | 类型检查 (`tsc --noEmit`) |

### 2.7 包管理

| 技术 | 选型 | 理由 |
|------|------|------|
| **pnpm** | 包管理器 | 硬链接省磁盘，严格依赖隔离防幽灵依赖；Docker 构建镜像体积更小；与后端 `uv` 理念一致 |

---

## 三、后端 (Phase 2: React 全栈期)

### 3.1 核心框架

| 技术 | 选型 | 理由 |
|------|------|------|
| **语言** | Python 3.13 | 与现有 CLI 版分析引擎同语言，直接复用 `review-analyzer-skill/src/` 所有模块 |
| **Web 框架** | FastAPI | 异步原生支持（任务状态 SSE 推送）；自动生成 OpenAPI/Swagger 文档；Pydantic 深度集成；性能接近 Node.js |
| **ASGI 服务器** | Uvicorn + Gunicorn (worker 模式) | 生产级部署，多 worker 处理并发请求 |

### 3.2 数据层

| 技术 | 选型 | 理由 |
|------|------|------|
| **ORM** | SQLAlchemy 2.0 (async 模式) | Python 生态标准 ORM，2.0 支持原生 async/await，与 FastAPI 配合好 |
| **迁移** | Alembic | SQLAlchemy 官方迁移工具，自动生成迁移脚本，支持降级回滚 |
| **校验** | Pydantic v2 | FastAPI 内置，Rust 核心性能极快；`BaseModel` 定义请求/响应 schema |
| **主数据库** | PostgreSQL 16 | 成熟稳定，JSONB 支持（标签数据、报告结构），全文搜索（评论检索） |
| **缓存/队列** | Redis 7 | Celery broker + result backend；Session 缓存；API 限流计数器 |
| **文件存储** | MinIO | S3 兼容，Docker 单容器部署，自托管零成本；存储导出文件（PDF/HTML/CSV）、评论图片 |

### 3.3 任务队列

| 技术 | 选型 | 理由 |
|------|------|------|
| **任务队列** | Celery + Redis | Python 生态标准异步任务方案；分析任务耗时 5-15 分钟，必须异步执行 |
| **实时推送** | SSE (Server-Sent Events) | Phase 1→5 进度实时推送到前端；比 WebSocket 更简单，单向推送即可 |

### 3.4 AI 引擎集成

| 阶段 | 方案 | 理由 |
|------|------|------|
| **Phase 1 (Streamlit)** | `subprocess` 调用 `claude --print` | 零额外成本，直接复用现有代码，利用用户已有 Claude 配额 |
| **Phase 2 (React)** | 同上 + 评估 Anthropic API 直调 | API 方式可扩展性更好（并发控制、错误处理、流式输出）；保留 CLI 模式作为配置选项 |

### 3.5 认证与安全

| 技术 | 选型 | 理由 |
|------|------|------|
| **认证** | JWT (python-jose) + bcrypt | 无状态，自托管友好（不需要外部 OAuth 提供商） |
| **OAuth (可选)** | Google / GitHub (P2) | 降低注册门槛，仅 Phase 2 后期添加 |
| **限流** | slowapi (基于 Redis) | 每用户每分钟 60 次 API 调用 |

### 3.6 测试

| 技术 | 用途 | 理由 |
|------|------|------|
| **单元测试** | pytest + pytest-cov + pytest-asyncio | Python 测试标准，异步支持完善 |
| **集成测试** | httpx (FastAPI TestClient 异步) | 测试完整 API 链路（含数据库事务回滚） |
| **E2E** | Playwright (复用前端 E2E 套件) | 关键用户流程端到端验证 |
| **覆盖率目标** | ≥ 80% | 核心分析引擎（review_analyzer / persona / insights）要求 ≥ 90% |
| **Mock 策略** | CLI 调用层 mock（不实际调用 claude），其余真实测试 | 测试速度快，CI 无需安装 claude CLI |

### 3.7 代码质量

| 技术 | 用途 |
|------|------|
| **ruff** | Lint + Format（替代 flake8/isort/black），Rust 实现，毫秒级 |
| **mypy** | 类型检查 (strict mode) |

---

## 四、前端 (Phase 1: Streamlit 验证期)

Phase 1 是快速验证阶段，技术栈极简：

| 技术 | 用途 |
|------|------|
| **Streamlit** | Web UI（单页面：ASIN 输入 → 进度条 → 看板嵌入） |
| **SQLite** | 任务历史存储（`st.cache_data` 辅助缓存） |
| **同进程调用** | `import review_analyzer` 直接运行现有模块，零改造 |

Phase 1 不引入前端构建工具链、任务队列和独立后端 —— 这一切留到 Phase 2。

---

## 五、DevOps

### 5.1 容器化

| 技术 | 用途 |
|------|------|
| **Docker** | 多阶段构建（Python: `python:3.13-slim`，Node: `node:22-alpine`） |
| **Docker Compose** | 一键启动全部服务：backend + frontend + PostgreSQL + Redis + MinIO |

### 5.2 CI/CD

| 技术 | 用途 |
|------|------|
| **GitHub Actions** | 公开仓库无限免费；PR 触发 lint → test → build；main 分支自动构建 Docker 镜像 |
| **GitHub Container Registry** | Docker 镜像发布 (`ghcr.io/buluslan/review-analyzer`) |
| **Renovate / Dependabot** | 依赖自动更新 PR |

CI Pipeline 流程：
```
PR 提交 → lint (ruff + biome) → type check (mypy + tsc) → unit test → integration test
                                                                          ↓
main merge → build Docker images → push to GHCR → (未来) E2E smoke test
```

### 5.3 日志与监控

| 阶段 | 技术 | 用途 |
|------|------|------|
| **Phase 1 / Phase 2 基础** | structlog | 结构化 JSON 日志，`docker logs` 直接查看，零外部依赖 |
| **Phase 2 进阶（可选）** | Sentry + Prometheus | 通过独立 `docker-compose.observability.yml` 可选开启，不强制 |

---

## 六、关键技术决策记录 (ADR)

以下记录 PRD 和本讨论中确定的关键决策及其理由。

### ADR-001: 为什么是 Next.js 而非 Vite SPA？

- **决策**：Next.js 15（App Router，SPA 模式为主）
- **理由**：
  - 分享链接功能（PRD §2.4）可能需要服务端渲染标题/OG 标签，Next.js 原生支持
  - 虽然当前是 SPA，但 Next.js 可以在需要 SSR 的页面（如公开分享页）选择性开启
  - Vite 纯 SPA 在需要 SSR 时只能重写，迁移成本高
  - Next.js Docker 自托管已经很成熟（`next start` 即可）

### ADR-002: 为什么是 Zustand 而非 Redux Toolkit？

- **决策**：Zustand
- **理由**：
  - 本项目状态复杂度中等偏低，不需要 Redux 的 action/reducer/slice 分层
  - Zustand ~1KB，API 3 个核心方法（`create` / `getState` / `setState`）
  - 开源项目新贡献者 10 分钟即可理解，降低贡献门槛
  - 与 TanStack Query 分工明确：Zustand 管 UI 状态，React Query 管服务端缓存

### ADR-003: 为什么是 pnpm 而非 npm？

- **决策**：pnpm
- **理由**：
  - 与后端 `uv` 理念一致（高效依赖管理 + 严格隔离），前后端策略统一
  - Docker 构建时硬链接缓存能显著减小镜像层大小
  - 严格依赖隔离避免"本地能跑 CI 报错"的幽灵依赖问题

### ADR-004: 为什么 Phase 1 不用 Celery？

- **决策**：Phase 1 (Streamlit) 不引入 Celery
- **理由**：
  - Streamlit 验证期面向单用户使用，无需任务队列
  - 分析任务直接在 Streamlit 进程中跑，简化部署（1 个容器 vs 4+ 个容器）
  - Phase 2 需要多用户并发时再通过 Celery 异步化，届时分析引擎函数签名不变，迁移成本低

### ADR-005: 为什么不直接用 Anthropic API 替代 CLI？

- **决策**：Phase 1 用 CLI subprocess，Phase 2 评估 API 迁移
- **理由**：
  - CLI 模式利用用户已有的 Claude Code 订阅，项目自身零 AI 成本 —— 这对开源免费定位至关重要
  - API 模式需要用户自己提供 API Key 并付费，增加使用门槛
  - 长期方案：支持双模式（CLI 直调 / API Key），用户按需选择

### ADR-006: 为什么日志先只用 structlog 不加 Sentry？

- **决策**：Phase 1/2 基础仅用 structlog
- **理由**：
  - "Docker Compose 一键启动"是核心体验，每多一个外部依赖容器就多一分上手阻力
  - structlog 零外部依赖，结构化日志通过 `docker logs` 直接查看
  - Sentry / Prometheus 作为 `docker-compose.observability.yml` 可选叠加，不强制

---

## 七、依赖清单速查

### 7.1 Python (backend)

```
# Web 框架
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
gunicorn>=23.0.0

# 数据层
sqlalchemy[asyncio]>=2.0.36
alembic>=1.14.0
asyncpg>=0.30.0
psycopg2-binary>=2.9.10   # SQLite 场景用
redis>=5.2.0
minio>=7.2.0

# 任务队列
celery[redis]>=5.4.0

# 认证
python-jose[cryptography]>=3.3.0
bcrypt>=4.2.0

# 数据校验（FastAPI 自带）
pydantic>=2.10.0

# 日志
structlog>=24.4.0

# 现有分析引擎依赖（复用）
pandas>=2.2.0
jinja2>=3.1.0
requests>=2.32.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0
tqdm>=4.66.0

# 开发/测试
pytest>=8.3.0
pytest-cov>=6.0.0
pytest-asyncio>=0.24.0
httpx>=0.28.0
ruff>=0.8.0
mypy>=1.13.0
```

### 7.2 Node.js (frontend)

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.60.0",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "rehype-highlight": "^7.0.0",
    "mermaid": "^11.0.0",
    "react-hook-form": "^7.53.0",
    "@hookform/resolvers": "^3.9.0",
    "zod": "^3.23.0",
    "tailwindcss": "^4.0.0",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "@types/react": "^19.0.0",
    "@types/node": "^22.0.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@playwright/test": "^1.49.0",
    "@biomejs/biome": "^1.9.0"
  }
}
```

### 7.3 Docker

| 镜像 | 用途 |
|------|------|
| `python:3.13-slim` | Backend + Celery worker |
| `node:22-alpine` | Frontend build → static files |
| `postgres:16-alpine` | 主数据库 |
| `redis:7-alpine` | 缓存 + 消息队列 broker |
| `minio/minio:latest` | S3 兼容文件存储 |
| `nginx:alpine` (可选) | 反向代理（多服务统一入口） |

---

## 八、Phase 1 vs Phase 2 对比

| 维度 | Phase 1 (Streamlit) | Phase 2 (React 全栈) |
|------|---------------------|----------------------|
| 上线周期 | 2-3 周 | 4-6 周 |
| 前端框架 | Streamlit (Python) | Next.js 15 + React 19 |
| UI 组件 | Streamlit 原生组件 | shadcn/ui + Tailwind CSS |
| 状态管理 | `st.session_state` | Zustand + TanStack Query |
| 后端框架 | Streamlit 内置 | FastAPI + Celery |
| 数据库 | SQLite (单文件) | PostgreSQL 16 |
| 任务调度 | 同步/后台线程 | Celery + Redis |
| 文件存储 | 本地文件系统 | MinIO (S3) |
| 用户系统 | 无 | JWT + bcrypt |
| 实时推送 | `st.progress()` | SSE (Server-Sent Events) |
| 容器数量 | 1 | 5-6 (backend + frontend + PG + Redis + MinIO + nginx) |
| AI 成本 | 用户已有 Claude 配额 | 用户已有 Claude 配额 (CLI) 或 API Key |
| 测试 | pytest (后端核心) | pytest + Vitest + Playwright × 前后端 |
| 6 套主题 | Jinja2 服务端渲染 | React 组件重写（复用 CSS 变量体系） |
```

