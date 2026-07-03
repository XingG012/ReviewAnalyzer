# 项目架构文档

> 本文档描述 ReviewAnalyzer 的代码架构、模块职责和数据流。
> 新增功能或重大重构后，必须更新本文档。

---

## 一、高层架构

```
┌─────────────────────────────────────────┐
│              用户交互层                    │
│  CLI (main.py)  │  Streamlit (待实现)     │
│  命令行向导+参数  │  Web UI (Phase 1 MVP)  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│              分析引擎层                    │
│  review-analyzer-skill/src/              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │Phase 2   │ │Phase 3   │ │Phase 4   │ │
│  │打标引擎   │ │画像分析   │ │报告生成   │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐              │
│  │Phase 1   │ │Phase 5   │              │
│  │数据获取   │ │输出管理   │              │
│  └──────────┘ └──────────┘              │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│              AI 引擎层                    │
│  Claude Code CLI (subprocess)            │
│  claude --print --dangerously-...        │
└─────────────────────────────────────────┘
```

---

## 二、模块职责

### 2.1 数据接入层 — `data_fetchers/`

| 文件 | 职责 | 依赖 |
|------|------|------|
| `base.py` | `DataFetcher` 抽象基类，定义 `fetch()` / `validate_config()` / `list_fields()` 接口 | 无 |
| `csv_fetcher.py` | CSV 文件读取 + 模糊列名匹配 + 字段标准化 | base.py |
| `sorftime_fetcher.py` | Sorftime 平台 API 对接 | base.py, requests |

**扩展方式**：新增平台只需继承 `DataFetcher`，实现 4 个抽象方法，注册到 `__init__.py`。

### 2.2 分析引擎 — Phase 2-4

| 文件 | Phase | 职责 | 核心函数 |
|------|-------|------|----------|
| `review_analyzer.py` | 2 | 批量 AI 打标（22 维度），ThreadPoolExecutor 并发，每批 20-50 条，失败重试 3 次 | `analyze_all()` |
| `user_persona_analyzer.py` | 3 | 场景×性别交叉画像识别，动态阈值，维度退化兜底，黄金样本筛选（3正+3负） | `analyze_user_personas()` |
| `insights_generator.py` | 4 | 14 章洞察报告生成，Mermaid 图表自动补全，strategic_json 结构化数据 | `calculate_stats_summary()`, `generate_insights()` |

### 2.3 输出层 — Phase 5

| 文件 | 职责 |
|------|------|
| `output_manager.py` | 统一输出调度：MD 报告 + HTML 看板 + 飞书同步 |
| `report_generator.py` | V1 HTML 看板生成（早期版本） |
| `template_engine.py` | V2 Jinja2 模板引擎：6 套主题，共享 base HTML + CSS |
| `chart_engine.py` | Chart.js 图表配置生成（饼图、柱状图、雷达图等） |
| `feishu_sync.py` | 飞书文档 + 画板图表同步 |

### 2.4 基础设施

| 文件 | 职责 |
|------|------|
| `config.py` | 全局配置单例（`Config` dataclass），CLI 引擎探测，路径管理，环境变量读取 |
| `data_loader.py` | 通用数据加载工具（CSV 解析、列名映射） |
| `prompts/manager.py` | Prompt 模板管理，V2 提示词路由 |
| `prompts/templates.py` | 各 Phase 的 Prompt 模板字符串 |

---

## 三、数据流

### 3.1 完整分析流程

```
用户输入 (CSV/ASIN)
    │
    ▼
Phase 1: data_fetchers/
    │  输出: 标准化评论列表 list[dict]
    │  字段: review_id, title, body, rating, author, date, ...
    ▼
Phase 2: review_analyzer.py
    │  输出: 带标签的评论列表
    │  新增字段: tags (22维), sentiment, info_score
    ▼
Phase 3: user_persona_analyzer.py
    │  输出: personas (List[Dict]), golden_samples (List[Dict])
    │  画像结构: {name, count, tags, dimension, color}
    │  样本结构: {review_id, body, rating, sentiment, persona_name, ...}
    ▼
Phase 4: insights_generator.py
    │  输入: tagged_reviews + personas + golden_samples
    │  输出: insights_md (str), stats (dict), strategic_json (dict)
    ▼
Phase 5: output_manager.py
    │  输入: 以上所有产物
    │  输出:
    │    ├── 评论采集及打标数据_{ASIN}.csv
    │    ├── 分析洞察报告_{ASIN}.md
    │    ├── 可视化洞察报告_{ASIN}.html (V1)
    │    └── {template}_看板.html (V2，可选模板)
    ▼
用户获得: CSV + MD + HTML 看板 (+ 飞书文档)
```

### 3.2 Phase 间耦合

- **Phase 1→2**：通过标准化 dict 列表传递，字段约定在 `data_fetchers/base.py`
- **Phase 2→3**：通过 tagged_reviews (list[dict])，tags 字段包含完整 22 维标签
- **Phase 2+3→4**：stats summary 由 `calculate_stats_summary()` 从 tagged_reviews 提取，personas 和 golden_samples 由 Phase 3 产出
- **Phase 4→5**：所有产物以 dict 形式传入 `output_manager.generate_outputs()`

---

## 四、关键设计决策

### 4.1 为什么 Phase 间不通过文件系统传递？

前 4 个 Phase 在**内存**中通过 Python 对象传递，只有 Phase 5 才写文件。这样的好处：
- 中间产物不需要写磁盘，避免 I/O 瓶颈
- 不产生中间临时文件，输出目录干净
- 便于 Web 版直接获取结构化分析结果，不用再解析 CSV/MD

### 4.2 为什么画像只用了「场景+性别」两个维度？

22 个维度的全交叉组合会产生指数级爆炸（例如"家用_女性_高收入_一线城市_..."），每个组合可能只有 1-2 人，毫无统计意义。场景×性别 是区分度 + 数据密度 的最佳平衡点。维度退化兜底保证了即使数据稀少也能产出有意义的画像。

### 4.3 为什么 Phase 2 不直接调用 Anthropic API？

- 零成本：利用用户已有 Claude Code 订阅配额
- 零配置：不需要用户额外申请 API Key
- Phase 2（React 全栈期）会评估 API 直调方案作为可选配置

### 4.4 模板系统的共享基座架构

```
base/
├── dashboard_base.html    ← 共享 HTML 骨架（所有主题共用）
└── dashboard_base.css     ← 共享核心 CSS（布局 + 通用组件）

{theme}/
├── theme.css              ← 仅覆盖颜色、字体、圆角等变量
└── meta.json              ← 主题元数据（名称、描述、作者）
```

新增主题只需写一个 `theme.css`（约 100-200 行），无需修改任何 HTML。

---

## 五、待实现（Phase 1 Streamlit）

参考 [implementation_plan.md](../implementation_plan.md) 的 12 个步骤：

- `streamlit_app/app.py` — Streamlit 主入口
- `streamlit_app/pipeline.py` — 封装 5 Phase 调用的生成器函数
- `streamlit_app/db.py` — SQLite 任务持久化
- `streamlit_app/Dockerfile` — 容器化部署
- `docker-compose.yml` — 一键启动

现有模块 (`review-analyzer-skill/src/`) **零改动**，Web 层直接 import 复用。
