# ReviewAnalyzer Web —— 产品需求文档 (PRD)

> 版本: v1.0 | 日期: 2026-07-03 | 状态: 草案

---

## 一、产品概述

### 1.1 产品定位

**ReviewAnalyzer Web** 是面向跨境电商从业者的一站式评论分析 SaaS 平台。用户输入 Amazon 产品 ASIN，系统自动爬取评论数据，通过 AI 引擎完成 22 维度深度打标与 14 章洞察报告生成，最终以交互式可视化看板呈现分析结果。

### 1.2 与当前 CLI 版本的关系

当前 [review-analyzer-skill](review-analyzer-skill/) 是 CLI 工具，已具备完整分析能力（4 Phase 流程、22 维标签、14 章报告、6 套可视化模板）。Web 版是在此基础上的产品化升级：

| 维度 | CLI 版 (当前) | Web 版 (目标) |
|------|-------------|-------------|
| 交互方式 | 命令行 + 交互式向导 | Web 页面，输入 ASIN 即用 |
| 数据获取 | 手动上传 CSV / Sorftime | 输入 ASIN 自动爬取 |
| 结果查看 | 本地文件夹打开 | 在线看板，任何设备可访问 |
| 历史管理 | 无 | 数据库持久化，可回溯历史 |
| 多用户 | 不支持 | 账号体系，每人独立数据 |
| 部署 | 本地 Python 环境 | Docker 一键部署，云端或自托管 |

### 1.3 目标用户

**主要用户**：跨境电商运营人员、产品经理、品牌方

- 日常需要做竞品分析的 Amazon 卖家
- 需要验证产品市场契合度的品牌方
- 需要批量分析多产品评论的团队

**用户痛点**：
1. 手动翻看 Amazon 评论页效率低，难以系统化提取洞察
2. 现有工具要么太贵（Jungle Scout / Helium 10 月费 $50+），要么分析深度不够
3. 分析结果散落各处，无法统一管理和回溯

---

## 二、功能需求

### 2.1 用户系统 (P0)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 注册/登录 | 邮箱注册 + 密码登录，支持 OAuth (Google/GitHub) | P0 |
| 个人中心 | 查看个人信息、使用配额、API 用量 | P1 |
| 会话管理 | JWT token 认证，7 天有效期 | P0 |

### 2.2 分析任务 (P0)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 创建分析 | 输入 ASIN + 站点（US/UK/DE/JP 等），启动分析任务 | P0 |
| 任务状态 | 实时展示任务进度：爬取中 → 打标中 → 报告生成中 → 完成 | P0 |
| 任务历史 | 列表展示所有历史分析任务，支持搜索和筛选 | P0 |
| 重新分析 | 对已完成任务重新触发分析（更新评论数据） | P1 |
| 批量分析 | 一次输入多个 ASIN，批量创建任务 | P2 |

### 2.3 评论爬取 (P0)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Amazon 评论爬虫 | 根据 ASIN + 站点，爬取商品评论（正文、评分、日期、图片等） | P0 |
| 爬取配置 | 可配置爬取数量上限（默认 500 条）、排序方式（最新/最有用） | P1 |
| 反爬策略 | IP 代理池 + User-Agent 轮换 + 请求频率控制 | P0 |
| 多站点支持 | 初期支持 US/UK/DE，后续扩展更多 Amazon 站点 | P1 |

### 2.4 AI 分析引擎 (P0)

复用现有 CLI 版分析能力，封装为后台异步任务：

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 22 维打标 | Phase 1：AI 批量打标，并发处理 | P0 |
| 用户画像 | Phase 2：场景+性别交叉画像识别 | P0 |
| 14 章报告 | Phase 3：深度洞察报告生成（含 mermaid 图表） | P0 |
| 可视化看板 | Phase 4：6 套主题 HTML 看板在线渲染 | P0 |
| 报告导出 | 支持导出 PDF / Markdown / CSV | P1 |

### 2.5 可视化看板 (P0)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 在线看板 | Web 端直接展示交互式看板（Chart.js 图表 + 玻璃拟态 UI） | P0 |
| 主题切换 | 6 套主题一键切换（premium-gold / dark-tech / linear-minimal 等） | P1 |
| 分享链接 | 生成只读分享链接，便于发给同事/客户查看 | P1 |
| 数据下载 | 打标 CSV、洞察报告 MD、看板 HTML 一键下载 | P0 |

### 2.6 通知与告警 (P2)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 任务完成通知 | 分析完成后邮件/站内通知 | P2 |
| 配额提醒 | API 用量接近上限时提醒 | P2 |

---

## 三、技术架构

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│           React + TypeScript + Tailwind CSS             │
│           Chart.js + 响应式设计                          │
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

| 层 | 技术 | 理由 |
|----|------|------|
| **前端** | React + TypeScript + Tailwind CSS | 生态成熟，组件库丰富，类型安全 |
| **图表** | Chart.js | 与已有 6 套模板兼容，无需重建 |
| **后端** | Python FastAPI | 与现有分析引擎语言一致，异步支持好，自动生成 API 文档 |
| **任务队列** | Celery + Redis | Python 生态首选，支持重试、优先级、监控 |
| **爬虫** | httpx + BeautifulSoup / Playwright | 轻量级页面抓取；必要时无头浏览器渲染 |
| **数据库** | PostgreSQL | 结构化数据（用户、任务、评论、分析结果） |
| **缓存** | Redis | Session、任务状态、临时数据 |
| **文件存储** | MinIO (兼容 S3) | 报告文件（HTML/PDF）、头像等静态资源 |
| **部署** | Docker Compose | 一键启动全部服务 |

### 3.3 数据库设计（核心表）

```
users                          # 用户表
├── id (UUID, PK)
├── email (UNIQUE)
├── password_hash
├── name
├── quota_total (INT)          # 总配额（分析次数）
├── quota_used (INT)
├── created_at
└── updated_at

tasks                          # 分析任务表
├── id (UUID, PK)
├── user_id (FK → users.id)
├── asin (VARCHAR(10))
├── site (VARCHAR(5))          # US/UK/DE/JP
├── status (ENUM)              # pending/crawling/tagging/reporting/done/failed
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

### 3.4 API 设计（核心接口）

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

### 4.1 页面结构

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

### 4.2 核心页面原型思路

**首页**：简洁的 ASIN 输入框 + 站点选择 + "开始分析"按钮。下方展示产品价值点（22 维度标签 / 14 章报告 / 6 套主题）。

**用户仪表盘**：左栏展示历史分析列表（状态标签、时间、ASIN），右栏是快速创建区域。

**分析详情页**：顶部进度条（爬取→打标→报告），完成后切换为嵌入式看板（复用现有 6 套 HTML 模板，以 iframe 或 SSR 方式嵌入）。

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
- 爬虫 IP 池隔离，避免牵连主服务

### 5.3 可维护性

- Docker Compose 一键部署
- 前后端分离，独立开发/部署
- 分析引擎作为独立模块，可脱离 Web 层单独升级
- 完整的 API 文档（FastAPI 自动生成 Swagger）

---

## 六、与现有代码的关系

```
ReviewAnalyzer/                         # 当前仓库
├── review-analyzer-skill/              # 现有分析引擎（保留，核心复用）
│   └── src/
│       ├── review_analyzer.py          # → 被 Celery task 调用
│       ├── user_persona_analyzer.py    # → 被 Celery task 调用
│       ├── insights_generator.py       # → 被 Celery task 调用
│       ├── template_engine.py          # → API 渲染 HTML 看板
│       └── chart_engine.py             # → API 返回图表 JSON
│
├── backend/                            # 新增：Web 后端
│   ├── app/
│   │   ├── main.py                     # FastAPI 入口
│   │   ├── api/                        # 路由层
│   │   ├── models/                     # SQLAlchemy 模型
│   │   ├── services/                   # 业务逻辑
│   │   ├── tasks/                      # Celery 任务
│   │   └── crawler/                    # Amazon 爬虫
│   ├── alembic/                        # 数据库迁移
│   └── Dockerfile
│
├── frontend/                           # 新增：Web 前端
│   ├── src/
│   │   ├── pages/                      # 页面组件
│   │   ├── components/                 # 通用组件
│   │   ├── hooks/                      # 自定义 Hook
│   │   ├── services/                   # API 调用
│   │   └── styles/                     # Tailwind + 主题
│   └── Dockerfile
│
├── docker-compose.yml                  # 新增：一键部署
└── PRD.md                              # 本文件
```

**复用策略**：`review-analyzer-skill/src/` 下所有分析模块作为独立的 Python 包被后端 import，Celery task 直接调用 `analyze_all()`、`generate_insights()` 等函数。前端 HTML 模板通过 API 由 `template_engine.render()` 服务端渲染后返回。

---

## 七、里程碑规划

### Phase 1: MVP（核心闭环）—— 4 周

- [ ] 用户注册/登录（JWT）
- [ ] 输入 ASIN → 自动爬取 → 分析 → 看板展示
- [ ] 任务状态实时推送（SSE）
- [ ] 任务历史列表
- [ ] 1 套看板主题（premium-gold）
- [ ] PostgreSQL + Redis 基础部署
- [ ] Docker Compose 一键启动

### Phase 2: 体验增强 —— 2 周

- [ ] 6 套主题全部接入 + 主题切换
- [ ] 报告导出（MD / CSV / HTML 下载）
- [ ] 分享链接（只读）
- [ ] 看板内标签筛选交互

### Phase 3: 产品化 —— 2 周

- [ ] 批量分析（多 ASIN）
- [ ] 竞品对比报告（跨 ASIN 分析）
- [ ] 配额系统 + 使用统计
- [ ] 邮件通知

### Phase 4: 商业化 —— 后续

- [ ] 付费订阅（Stripe 集成）
- [ ] 团队协作（多成员 / 共享看板）
- [ ] 多平台支持（eBay / Shopify / Walmart）
- [ ] 自定义标签体系

---

## 八、风险与假设

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Amazon 反爬升级 | 爬虫不可用 | 备选数据源（Sorftime API / 第三方数据商）；用户手动上传 CSV 兜底 |
| AI CLI 依赖不稳定 | 分析失败 | 增加重试机制；考虑备用 LLM API（如直接调 Anthropic API） |
| 分析耗时长（> 15min） | 用户体验差 | 异步任务 + 进度推送 + 完成后通知；优化批次并发 |
| 服务器成本 | 运营压力 | 支持自托管部署（Docker）；云端按需选配 |

---

## 九、附录

### A. 竞品参考

| 产品 | 定位 | 月费 | 差异 |
|------|------|------|------|
| Jungle Scout | 全功能卖家工具 | $49+ | 侧重选品 + 关键词，分析浅 |
| Helium 10 | 全功能卖家工具 | $39+ | 侧重 Listing 优化，报告单一 |
| ReviewAnalyzer Web | 专注评论深度分析 | 待定 | AI 深度洞察 + 可视化，分析维度远多于竞品 |

### B. 关键指标 (North Star)

- **分析完成率**：创建任务 → 看板可用的比例（目标 > 95%）
- **时间到价值**：从输入 ASIN 到可查看报告的时间（目标 < 10 分钟）
- **周活用户**：每周至少完成 1 次分析的用户数
