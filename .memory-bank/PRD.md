# ReviewAnalyzer Web —— 产品需求文档 (PRD)

> 版本: v1.1 | 日期: 2026-07-03 | 状态: 草案
>
> v1.1 修订：统一 14 章 + 5 Phase 口径；明确"先 Streamlit 验证，再 React SPA 全栈"的渐进路线；确定开源免费 + 自托管的商业化模式。

---

## 一、产品概述

### 1.1 产品定位

**ReviewAnalyzer** 是面向跨境电商从业者的开源评论分析平台。用户输入 Amazon 产品 ASIN 或上传评论 CSV，系统通过 AI 引擎完成 22 维度深度打标与 14 章洞察报告生成，最终以交互式可视化看板呈现分析结果。

核心特点：
- **开源免费**：MIT 协议，Docker 一键自托管，无月费
- **零 API Key 依赖**：AI 引擎基于 Claude Code CLI，利用用户已有 Claude 配额
- **分析深度远超竞品**：22 维标签 × 14 章报告 × 6 套可视化主题

### 1.2 与当前 CLI 版本的关系

当前 [review-analyzer-skill](review-analyzer-skill/) 是 CLI 工具，已具备完整分析能力（5 Phase 流程、22 维标签、14 章报告、6 套可视化模板）。Web 版是在此基础上的产品化升级：

| 维度 | CLI 版 (当前) | Web 版 (目标) |
|------|-------------|-------------|
| 交互方式 | 命令行 + 交互式向导 | Web 页面，输入 ASIN 即用 |
| 数据获取 | 手动上传 CSV / Sorftime API | Amazon 爬虫 → 第三方 API（Sorftime / Keepa）→ CSV 上传，三级降级 |
| 结果查看 | 本地文件夹打开 | 在线看板，任何设备可访问 |
| 历史管理 | 无 | 数据库持久化，可回溯历史 |
| 多用户 | 不支持 | 可选账号体系，每人独立数据 |
| 部署 | 本地 Python 环境 | Docker 一键部署，自托管 |

5 Phase 流程：

```
Phase 1: 数据获取  →  Phase 2: AI 打标  →  Phase 3: 用户画像  →  Phase 4: 洞察报告  →  Phase 5: 输出看板
    (爬虫/API/CSV)    (22维标签+并发)      (场景×性别交叉)      (14章+mer maid)     (6套主题HTML)
```

### 1.3 目标用户

**主要用户**：跨境电商运营人员、产品经理、品牌方

- 日常需要做竞品分析的 Amazon 卖家
- 需要验证产品市场契合度的品牌方
- 需要批量分析多产品评论的团队
- 注重数据隐私、希望自托管的企业用户

**用户痛点**：
1. 手动翻看 Amazon 评论页效率低，难以系统化提取洞察
2. 现有工具要么太贵（Jungle Scout / Helium 10 月费 $50+），要么分析深度不够
3. 分析结果散落各处，无法统一管理和回溯
4. SaaS 工具数据上传至第三方服务器，存在隐私顾虑

---

## 二、功能需求

### 2.1 数据获取 (P0)

三级降级策略，确保数据可用性：

| 优先级 | 数据源 | 描述 |
|--------|--------|------|
| **首选** | Amazon 爬虫 | 集成开源 Amazon 评论爬虫模块，输入 ASIN 自动抓取评论（正文、评分、日期、图片、Verified 标记等） |
| **降级 1** | 第三方 API | 对接 Sorftime API（已集成）、Keepa API 等第三方数据平台 |
| **兜底** | CSV 上传 | 用户手动上传评论 CSV，支持模糊列名匹配 |

爬虫相关功能：

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Amazon 评论抓取 | 根据 ASIN + 站点（US/UK/DE/JP），自动爬取评论 | P0 |
| 爬取配置 | 可配置数量上限（默认 500 条）、排序方式（最新/最有用） | P1 |
| 反爬策略 | IP 代理池 + User-Agent 轮换 + 请求频率控制 | P0 |
| 多站点支持 | 初期 US/UK/DE，后续扩展 | P1 |

### 2.2 分析任务 (P0)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 创建分析 | 输入 ASIN + 站点，或上传 CSV，启动分析任务 | P0 |
| 任务状态 | 实时展示 Phase 1→5 进度（数据获取 → 打标 → 画像 → 报告 → 完成） | P0 |
| 任务历史 | 列表展示所有历史分析任务，支持搜索和筛选 | P0 |
| 重新分析 | 对已完成任务重新触发分析（更新评论数据） | P1 |
| 批量分析 | 一次输入多个 ASIN，批量创建任务 | P2 |

### 2.3 AI 分析引擎 (P0)

复用现有 CLI 版 5 Phase 分析流程，封装为后台异步任务：

| Phase | 功能 | 描述 |
|-------|------|------|
| Phase 1 | 数据获取 | Amazon 爬虫 / Sorftime API / CSV 上传 |
| Phase 2 | 22 维打标 | AI 批量打标，ThreadPoolExecutor 并发（4 workers），每批 20-50 条 |
| Phase 3 | 用户画像 | 场景+性别交叉画像识别（最多 4 个画像），每画像 3 正+3 负黄金样本 |
| Phase 4 | 14 章报告 | 深度洞察报告生成（含 mermaid 图表 + strategic_json 结构化数据） |
| Phase 5 | 可视化看板 | 6 套主题 HTML 看板渲染（Chart.js + 玻璃拟态 UI）+ 数据下载 |

**AI 引擎实现方案**：
- **Phase 1（Streamlit 验证期）**：沿用 CLI subprocess 调用 `claude --print`，零额外成本，直接复用现有代码
- **Phase 2（React 全栈期）**：评估迁移至 Anthropic API 直接调用或混合模式（小请求用 API、长文本用 CLI），提升可扩展性和稳定性

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 报告导出 | 支持导出 PDF / Markdown / CSV / HTML | P1 |

### 2.4 可视化看板 (P1)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 在线看板 | Web 端直接展示交互式看板（Chart.js 图表 + 玻璃拟态 UI） | P0 |
| 主题切换 | 6 套主题一键切换（premium-gold / dark-tech / linear-minimal / posthog-analytics / stripe-executive / warm-editorial） | P1 |
| 分享链接 | 生成只读分享链接，便于发给同事/客户查看 | P2 |
| 数据下载 | 打标 CSV、洞察报告 MD、看板 HTML 一键下载 | P0 |

### 2.5 用户系统 (P2)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 注册/登录 | 邮箱注册 + 密码登录，可选 OAuth (Google/GitHub) | P2 |
| 个人中心 | 查看个人信息、分析历史 | P2 |
| 会话管理 | JWT token 认证 | P2 |

> 注：用户系统设计保留但降低优先级。Phase 1（Streamlit）不包含用户系统——任何部署实例的人都能直接使用。Phase 2（React 全栈）按需添加多用户支持。

### 2.6 通知 (P2)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 任务完成通知 | 分析完成后邮件/站内通知 | P2 |

---

## 三、技术架构

### 3.1 渐进式架构路线

```
Phase 1（验证期）: Streamlit 极简 Web
┌──────────────────────────────────────────┐
│        Streamlit（Python 原生 UI）         │
│    输入 ASIN → 后台 Pipeline → 看板展示    │
│          单文件部署，无需前端               │
└──────────────────┬───────────────────────┘
                   │ 直接调用（同进程）
┌──────────────────▼───────────────────────┐
│       review-analyzer-skill（分析引擎）     │
│   Phase 1 数据获取 → Phase 5 输出看板      │
└──────────────────────────────────────────┘

Phase 2（全栈期）: React SPA + FastAPI
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│           React + TypeScript + Tailwind CSS             │
│           Chart.js + 响应式设计                          │
│           6 套主题从 Jinja2 模板重写为 React 组件         │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/REST API
┌─────────────────────▼───────────────────────────────────┐
│                    Backend (API)                         │
│              Python FastAPI + Celery                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │
│  │ Auth     │  │ Task     │  │ Analysis Engine  │     │
│  │ Service  │  │ Queue    │  │ (复用现有模块)    │     │
│  └──────────┘  └──────────┘  └──────────────────┘     │
│  ┌──────────┐  ┌──────────────────────────────────┐    │
│  │ Crawler  │  │ Report / Export Service           │    │
│  │ Service  │  │ (PDF / MD / CSV / HTML)           │    │
│  └──────────┘  └──────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Data Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │
│  │PostgreSQL│  │  Redis   │  │  S3 / MinIO      │     │
│  │(主存储)   │  │(缓存/队列) │  │  (文件存储)       │     │
│  └──────────┘  └──────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 3.2 技术选型

| 层 | Phase 1（验证期） | Phase 2（全栈期） | 理由 |
|----|-------------------|-------------------|------|
| **前端** | Streamlit | React + TypeScript + Tailwind CSS | Phase 1 零前端成本快速验证；Phase 2 生态成熟、类型安全 |
| **图表** | Chart.js (嵌入) | Chart.js | 与已有 6 套模板兼容 |
| **后端** | Streamlit 内置 | Python FastAPI | 与现有分析引擎语言一致，自动生成 API 文档 |
| **任务队列** | 无（同步/简单后台线程） | Celery + Redis | 初期单用户场景无需队列 |
| **数据获取** | Amazon 爬虫（开源模块集成）→ Sorftime / Keepa API → CSV 上传 | 同左 | 三级降级保证数据可用性 |
| **数据库** | SQLite（轻量） | PostgreSQL | 初期单机 SQLite 即可；多用户场景迁 PG |
| **缓存** | 无 | Redis | Session、任务状态 |
| **文件存储** | 本地文件系统 | MinIO (兼容 S3) | 初期本地存储；扩展时迁对象存储 |
| **部署** | `docker compose up` | Docker Compose | 一键启动，自托管友好 |

### 3.3 数据库设计（Phase 2 全栈期，核心表）

```
users                          # 用户表
├── id (UUID, PK)
├── email (UNIQUE)
├── password_hash
├── name
├── created_at
└── updated_at

tasks                          # 分析任务表
├── id (UUID, PK)
├── user_id (FK → users.id, nullable)   # Phase 1 无用户系统时可为空
├── asin (VARCHAR(10))
├── site (VARCHAR(5))          # US/UK/DE/JP
├── status (ENUM)              # pending/fetching/tagging/reporting/rendering/done/failed
├── progress (INT)             # 0-100
├── error_message (TEXT)
├── config (JSONB)             # 分析配置快照
├── started_at
├── completed_at
└── created_at

reviews                        # 评论原始数据
├── id (UUID, PK)
├── task_id (FK → tasks.id)
├── review_id (VARCHAR(50))    # Amazon 原始 review_id
├── body (TEXT)
├── rating (FLOAT)
├── author (VARCHAR(100))
├── date (DATE)
├── helpful_count (INT)
├── images (JSONB)             # 评论图片 URL 列表
├── is_verified (BOOLEAN)
└── created_at

tagged_reviews                 # AI 打标结果（原表 + 标签列）
├── id (UUID, PK)
├── task_id (FK → tasks.id)
├── review_id (FK → reviews.id)
├── sentiment (VARCHAR(20))
├── info_score (INT)
├── tags (JSONB)               # 22 维度标签 {"人群_性别": "男性", ...}
└── created_at

personas                       # 用户画像
├── id (UUID, PK)
├── task_id (FK → tasks.id)
├── name (VARCHAR(100))        # 画像名如 "家用_女性"
├── count (INT)                # 该画像人数
├── tags (JSONB)               # 画像特征标签
├── color (VARCHAR(7))
└── created_at

analysis_reports               # 分析报告
├── id (UUID, PK)
├── task_id (FK → tasks.id, UNIQUE)
├── insights_md (TEXT)         # Markdown 洞察报告
├── stats (JSONB)              # 统计数据快照
├── strategic_json (JSONB)     # 战略数据（护城河/软肋/执行矩阵）
├── chart_configs (JSONB)      # 图表配置
├── html_content (TEXT)        # 渲染后的 HTML 看板
├── template_name (VARCHAR(50))
└── created_at

golden_samples                 # 黄金样本
├── id (UUID, PK)
├── task_id (FK → tasks.id)
├── persona_id (FK → personas.id)
├── review_id (FK → reviews.id)
├── sentiment (VARCHAR(20))
├── sentiment_class (VARCHAR(20))
└── created_at
```

### 3.4 API 设计（Phase 2 核心接口）

```
POST   /api/auth/register          # 注册
POST   /api/auth/login             # 登录
GET    /api/auth/me                 # 当前用户信息

POST   /api/tasks                   # 创建分析任务 {asin, site, options}
GET    /api/tasks                   # 任务列表（分页、搜索）
GET    /api/tasks/:id               # 任务详情（含状态、进度）
DELETE /api/tasks/:id               # 删除任务
POST   /api/tasks/:id/retry         # 重新分析

GET    /api/tasks/:id/reviews       # 评论数据（分页、支持标签筛选）
GET    /api/tasks/:id/tagged        # 打标数据
GET    /api/tasks/:id/personas      # 用户画像
GET    /api/tasks/:id/report        # 洞察报告（返回 Markdown）
GET    /api/tasks/:id/dashboard     # 看板数据（返回 HTML 或结构化 JSON）
GET    /api/tasks/:id/charts        # 图表配置（Chart.js 格式）
GET    /api/tasks/:id/export/:fmt   # 导出报告 (md/html/csv/pdf)

GET    /api/tasks/:id/status/stream # SSE 实时状态推送
```

---

## 四、页面规划

### 4.1 Phase 1（Streamlit）：单页面应用

Streamlit 天然单页面，通过侧边栏导航组织功能：

- **主页**：ASIN 输入框 + 站点选择 + CSV 上传区 + "开始分析"按钮
- **进度区**：Phase 1→5 实时进度条（Streamlit 原生 `st.progress()`）
- **结果区**：看板 HTML 内嵌展示（`st.components.v1.html()`）+ MD 报告渲染 + CSV/HTML 下载按钮

### 4.2 Phase 2（React SPA）：多页面应用

```
/                    首页 / Landing Page
/login               登录页
/register            注册页
/dashboard           用户仪表盘（任务列表 + 快速创建）
/tasks/:id           分析详情页（任务进度 / 看板嵌入）
/tasks/:id/report    洞察报告全文
/tasks/:id/reviews   评论详情（支持标签筛选）
/settings            个人设置
/admin               管理后台（P2）
```

### 4.3 核心页面原型思路

**首页**：简洁的 ASIN 输入框 + 站点选择 + CSV 上传区 + "开始分析"按钮。下方展示产品价值点（22 维度标签 / 14 章报告 / 6 套主题）。

**用户仪表盘**：左栏展示历史分析列表（状态标签、时间、ASIN），右栏是快速创建区域。

**分析详情页**：顶部进度条（数据获取→打标→画像→报告→看板），完成后切换为嵌入式看板。Phase 1 用 Streamlit 组件内嵌 HTML；Phase 2 用 React 组件重写 6 套主题（复用 Chart.js 图表配置）。

**报告页**：14 章 Markdown 渲染 + 锚点导航目录。

---

## 五、非功能需求

### 5.1 性能

| 指标 | 目标 |
|------|------|
| 单次分析耗时 (500 条评论) | < 15 分钟 |
| API 响应时间 (P99) | < 500ms |
| 并发分析任务数 | 10+ |
| 首页加载时间 (LCP) | < 2s |

### 5.2 安全

- 用户密码 bcrypt 加盐哈希存储
- JWT token + HTTPS 传输
- API 限流（每用户每分钟 60 次）
- SQL 注入防护（ORM 参数化查询）
- 爬虫 IP 池与主服务隔离

### 5.3 可维护性

- Docker Compose 一键部署（自托管场景核心体验）
- 前后端分离，独立开发/部署
- 分析引擎作为独立模块（`review-analyzer-skill/`），可脱离 Web 层单独升级
- 数据接入层抽象（`data_fetchers/`），新增平台只需实现一个 Fetcher 类
- 完整的 API 文档（FastAPI 自动生成 Swagger）

---

## 六、与现有代码的关系

```
ReviewAnalyzer/                         # 当前仓库
├── review-analyzer-skill/              # 现有分析引擎（保留，核心复用）
│   └── src/
│       ├── review_analyzer.py          # → Phase 2: AI 打标
│       ├── user_persona_analyzer.py    # → Phase 3: 用户画像
│       ├── insights_generator.py       # → Phase 4: 洞察报告
│       ├── template_engine.py          # → Phase 5: HTML 看板渲染
│       ├── chart_engine.py             # → Phase 5: Chart.js 图表配置
│       └── data_fetchers/              # → Phase 1: 数据接入层（可扩展）
│
├── streamlit_app/                      # Phase 1 新增：Streamlit 极简 Web
│   ├── app.py                          # Streamlit 入口
│   └── Dockerfile
│
├── backend/                            # Phase 2 新增：FastAPI 后端
│   ├── app/
│   │   ├── main.py                     # FastAPI 入口
│   │   ├── api/                        # 路由层
│   │   ├── models/                     # SQLAlchemy 模型
│   │   ├── services/                   # 业务逻辑
│   │   ├── tasks/                      # Celery 任务
│   │   └── crawler/                    # Amazon 爬虫模块
│   ├── alembic/                        # 数据库迁移
│   └── Dockerfile
│
├── frontend/                           # Phase 2 新增：React SPA
│   ├── src/
│   │   ├── pages/                      # 页面组件
│   │   ├── components/                 # 通用组件 + 6 套主题组件
│   │   ├── hooks/                      # 自定义 Hook
│   │   ├── services/                   # API 调用
│   │   └── styles/                     # Tailwind + 主题
│   └── Dockerfile
│
├── docker-compose.yml                  # Phase 1 起即提供
└── PRD.md                              # 本文件
```

**复用策略**：
- **Phase 1**：Streamlit 直接 import `review_analyzer.py` 等模块，同进程调用，零改造
- **Phase 2**：Celery task 调用 `analyze_all()`、`generate_insights()` 等函数；`template_engine.render()` 通过 API 服务端渲染；6 套 CSS 主题变量抽取为 Tailwind 设计 token

---

## 七、里程碑规划

### Phase 1: Streamlit 极简验证 —— 2-3 周

**目标**：最快速度上线可用 Web 版本，验证市场需求

- [ ] 集成开源 Amazon 爬虫模块（GitHub 找到的代码），实现 ASIN → 评论抓取
- [ ] Streamlit 简单 UI（ASIN 输入 + CSV 上传 + 进度条 + 看板嵌入）
- [ ] 直接调用现有 `main.py` 的 5 Phase 流程（同进程，无需 Celery）
- [ ] 看板 HTML 内嵌展示 + MD 报告渲染
- [ ] CSV / MD / HTML 下载
- [ ] SQLite 存储任务历史
- [ ] Docker Compose 一键部署
- [ ] 发布到 GitHub，收集早期用户反馈

### Phase 2: React 全栈产品化 —— 4-6 周

**目标**：基于验证反馈，建设正式产品

- [ ] FastAPI 后端 + Celery 任务队列
- [ ] React SPA 前端，6 套主题从 Jinja2 模板重写为 React 组件
- [ ] PostgreSQL + Redis 数据层
- [ ] 用户系统（注册/登录/JWT）
- [ ] 任务状态 SSE 实时推送
- [ ] 报告导出（PDF）
- [ ] 分享链接（只读）
- [ ] 爬虫降级方案完善（Sorftime / Keepa API 对接）
- [ ] 完整 API 文档（Swagger）

### Phase 3: 扩展与深化 —— 后续

- [ ] 批量分析（多 ASIN）
- [ ] 竞品对比报告（跨 ASIN 交叉分析）
- [ ] 飞书/钉钉/企业微信通知集成
- [ ] 多平台数据接入（eBay / Shopify / Walmart，架构已预留扩展点）
- [ ] 企业定制（自定义标签体系、品牌白标）
- [ ] 社区贡献生态（第三方数据源 Fetcher 插件）

---

## 八、风险与假设

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Amazon 反爬升级 | 爬虫不可用 | 三级降级：开源爬虫 → Sorftime / Keepa API → 用户手动 CSV 上传；爬虫模块独立更新 |
| Claude Code CLI 不稳定 | 分析失败或超时 | 内置重试机制（3 次）；后续评估迁移至 Anthropic API 直调 |
| 分析耗时长（> 15min） | 用户体验差 | 异步任务 + 进度推送 + 完成后通知；优化批次并发 |
| 6 套模板 React 重写工作量大 | Phase 2 延期 | 提炼 CSS 变量系统，一套组件多套皮肤；Phase 1 阶段先用 Jinja2 SSR 过渡 |
| 开源社区活跃度不足 | 项目停滞 | 完善的文档 + Docker 一键部署降低门槛；飞书/微信群提供用户支持 |

---

## 九、附录

### A. 竞品对比

| 产品 | 定位 | 价格 | ReviewAnalyzer 差异 |
|------|------|------|---------------------|
| Jungle Scout | 全功能卖家工具 | $49+/月 | 侧重选品+关键词；ReviewAnalyzer 专注评论深度分析，免费开源 |
| Helium 10 | 全功能卖家工具 | $39+/月 | 侧重 Listing 优化；ReviewAnalyzer 提供 14 章 AI 洞察 + 6 套看板 |
| ReviewAnalyzer | 专注评论深度分析 | **免费开源** | 自托管，数据不出服务器；分析维度远超商业竞品 |

### B. 商业模式

**开源免费 + 服务变现**：

- **免费**：MIT 协议开源，Docker 自托管，所有功能免费使用
- **增值服务（后续）**：
  - 企业定制（私有化部署支持、自定义标签体系、品牌白标）
  - 咨询培训（评论分析方法论、AI + 电商实践培训）
  - 托管服务（官方托管实例，免运维）

### C. 关键指标 (North Star)

- **分析完成率**：创建任务 → 看板可用的比例（目标 > 95%）
- **时间到价值**：从输入 ASIN 到可查看报告的时间（目标 < 10 分钟）
- **GitHub Stars**：开源项目关注度（核心增长指标）
- **自托管部署数**：Docker 镜像拉取量
