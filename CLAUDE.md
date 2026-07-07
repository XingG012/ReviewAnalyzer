# CLAUDE.md — ReviewAnalyzer 项目规则

> 本文件由 Claude Code 在每次会话启动时自动加载。
> 所有规则适用于本项目的任何 AI 编码助手（Claude Code / Codex CLI / Cursor 等）。

---

## Always Rules（始终生效）

```
# ── 文档驱动 ──
# ALWAYS: 写任何代码前，先读取 .memory-bank/architecture.md（包含完整数据库 schema）和 .memory-bank/PRD.md
# ALWAYS: 添加重大功能或完成里程碑后，更新 .memory-bank/architecture.md

# ── 实施流程 ──
# ALWAYS: 按 .memory-bank/implementation_plan.md 的步骤顺序执行，禁止跳过或并行
# ALWAYS: 每完成一个步骤：① 自动化验证（Playwright/curl/pytest）→ ② 提示用户手动验证 → ③ 用户确认通过后更新 .memory-bank/progress.md → ④ 才进入下一步

# ── 模块化（最高优先级） ──
# ALWAYS: 每个功能模块独立一个文件，严格禁止单文件超过 500 行
# ALWAYS: 新建文件前，先判断其职责是否可归入现有模块；能复用的绝不新建
# ALWAYS: 禁止创建 utils.py / helpers.py / common.py 等"万能杂物间"文件

# ── 代码质量 ──
# ALWAYS: 新增功能必须写测试，覆盖率目标 ≥ 80%
# ALWAYS: 后端代码遵循 Python 3.13+ 语法，使用 ruff 格式化和 mypy 类型检查
# ALWAYS: 前端代码使用 TypeScript strict mode，Biome 格式化和 lint
# ALWAYS: 所有 import 必须显式写出，禁止 import * 和未声明的隐式依赖
# ALWAYS: API 请求/响应必须用 Pydantic (后端) / Zod (前端) 校验
# ALWAYS: 敏感信息（API Key、密码）只能出现在 .env 中，禁止硬编码
```

---

## 项目概述

ReviewAnalyzer 是面向跨境电商从业者的开源评论分析平台。
- **定位**：MIT 开源，Docker 自托管，免费
- **AI 引擎**：Claude Code CLI subprocess 调用，零 API Key 成本
- **五阶段流水线**：数据获取 → AI 打标(22维) → 用户画像 → 14章洞察报告 → 可视化看板

## 技术栈速查

| 层 | Phase 1 (当前 CLI/Streamlit) | Phase 2 (React 全栈) |
|----|------------------------------|----------------------|
| 前端 | Streamlit | Next.js 15 + TypeScript + Tailwind CSS |
| 状态管理 | st.session_state | Zustand + TanStack Query |
| 后端 | Python (同进程) | FastAPI + Celery |
| 数据库 | SQLite | PostgreSQL 16 |
| 缓存/队列 | 无 | Redis 7 |
| 文件存储 | 本地 | MinIO |
| 图表 | Chart.js (Jinja2 SSR) | Chart.js (React 组件) |
| 部署 | 手动 | Docker Compose |
| 测试 | pytest | pytest + Vitest + Playwright |

详细技术选型及决策理由见 [tech_stack.md](.memory-bank/tech_stack.md)。

## 项目结构

```
ReviewAnalyzer/
├── review-analyzer-skill/      # 核心分析引擎（独立模块，可脱离 Web 层运行）
│   ├── main.py                 # CLI 入口（5 Phase 流程）
│   ├── replay_phase2to5.py     # 快速重放脚本（跳过 Phase 1）
│   ├── SKILL.md                # Claude Code Skill 定义
│   ├── src/
│   │   ├── config.py           # 全局配置（CLI 引擎、路径、并发等）
│   │   ├── review_analyzer.py  # Phase 2: AI 打标引擎（ThreadPoolExecutor 并发）
│   │   ├── user_persona_analyzer.py  # Phase 3: 用户画像识别
│   │   ├── insights_generator.py     # Phase 4: 14章洞察报告生成
│   │   ├── report_generator.py       # Phase 5: V1 HTML 看板
│   │   ├── template_engine.py        # Phase 5: V2 Jinja2 模板引擎
│   │   ├── output_manager.py         # Phase 5: 统一输出管理
│   │   ├── chart_engine.py           # Chart.js 图表配置
│   │   ├── data_loader.py            # CSV 数据加载
│   │   ├── feishu_sync.py            # 飞书文档同步
│   │   ├── data_fetchers/            # 数据接入层（可扩展）
│   │   ├── prompts/                  # Prompt 模板管理
│   │   └── templates/                # 6 套 HTML 可视化主题
│   ├── references/                   # 标签体系、CSV 格式等参考文档
│   └── tools/                        # 辅助工具脚本
├── streamlit_app/              # Phase 1: Streamlit Web (进行中)
├── backend/                    # (待实现) Phase 2: FastAPI 后端
├── frontend/                   # (待实现) Phase 2: Next.js 前端
├── .memory-bank/                # 项目文档记忆库
│   ├── PRD.md                   # 产品需求文档
│   ├── tech_stack.md            # 技术选型文档
│   ├── implementation_plan.md   # 实施计划
│   ├── architecture.md          # 代码架构文档
│   └── progress.md              # 进度跟踪
└── docker-compose.yml          # (待实现) Docker 部署配置
```

## 编码规范

### Python（后端 + 分析引擎）

```python
# 文件头：必须有 docstring 说明模块职责
"""
模块名称 — 一句话描述

详细说明（可选）
"""

# Imports 分四组，空行分隔：
# 1. 标准库
import os
from pathlib import Path

# 2. 第三方库
import pandas as pd

# 3. 项目内部模块
from src.config import config

# 4. 类型注解（仅 when needed）
from typing import List, Dict, Optional

# 类型注解：所有公开函数必须有
def analyze_reviews(reviews: List[Dict]) -> Dict[str, any]:
    """明确说明返回值结构"""
    ...

# 配置：统一使用 src.config 的 config 实例，不要各自读环境变量
# 错误示例：API_KEY = os.getenv("KEY")  # ❌
# 正确示例：from src.config import config; key = config.SORFTIME_API_KEY  # ✅
```

### TypeScript / React（前端）

```typescript
// 文件头：组件必须有 JSDoc
/** 任务列表组件 — 展示用户的所有分析任务 */
export function TaskList({ tasks }: TaskListProps) { ... }

// 类型优先：禁止 any，必要时用 unknown + type guard
// API 响应都用 Zod schema 校验

// 组件拆分：页面 → 功能区块 → UI 原子，每层独立文件
// pages/tasks/[id].tsx → components/TaskProgress.tsx → ui/ProgressBar.tsx
```

## 模块化规则（最高优先级）

> 这是整个项目可维护性的基石。AI 编码助手最大的坏习惯就是把所有逻辑塞进一个巨型文件——必须严防。

1. **单一职责**：每个文件只做一件事
   - ✅ `user_persona_analyzer.py` — 只负责画像识别
   - ❌ `utils.py` — 什么都往里扔 → **禁止创建此类文件**

2. **文件大小硬上限**：**500 行**。超过必须拆分，无例外。

3. **接口优于实现**：模块间通过明确的函数签名通信
   - data_fetchers 层定义了 DataFetcher 抽象类，新增数据源只需实现子类

4. **配置集中**：所有魔法数字、路径名、超时时间 → `src/config.py`

5. **复用现有模块，严禁重复造轮子**：Web 层直接 import 分析引擎函数
   ```python
   from src.review_analyzer import analyze_all              # ✅
   from src.user_persona_analyzer import analyze_user_personas  # ✅
   ```

6. **新建文件前自检**：
   - 这个功能是否属于某个已有模块？→ 归入已有模块
   - 这个文件未来会不会超过 500 行？→ 现在就该拆
   - 这个文件能否用一句话描述清楚职责？→ 不能就别建

## 分析流水线约定

```
Phase 1: data_fetchers/     → 标准化评论列表 (list[dict])
Phase 2: review_analyzer.py  → 22维标签 + info_score + sentiment
Phase 3: user_persona_analyzer.py → 画像列表 (4个) + 黄金样本 (每画像6条)
Phase 4: insights_generator.py   → MD洞察报告 + strategic_json
Phase 5: output_manager.py       → MD + HTML看板 + 飞书同步
```

- Phase 间通过**明确的数据结构**传递，不通过文件系统（Phase 5 输出除外）
- Phase 2 的 AI 调用通过 `config.build_cli_cmd()` 统一入口，禁止裸写 subprocess

## 测试规范

- 测试文件与源码同目录，命名为 `test_<模块名>.py`
- CLI 调用层 mock 掉（不实际调用 claude），其余逻辑真实测试
- 关键模块（review_analyzer / persona / insights）要求 ≥ 90% 覆盖率

## 常见陷阱

1. **不要修改 prompt 模板后忘记同步更新 SKILL.md 和 .memory-bank/PRD.md 中的描述**
2. **tag_system.yaml 是标签体系单一真实来源**，任何标签变更必须从此文件出发
3. **CLI 引擎通过环境变量 `CLI_ENGINE` 设置**，不要硬编码 claude 路径
4. **replay_phase2to5.py 的 Phase 编号是内部视角（Phase 2/4）**，main.py 是完整 5 Phase 视角（Phase 2/5），两者不同是正常的
