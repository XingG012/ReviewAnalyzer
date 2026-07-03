# ReviewAnalyzer

AI 驱动的电商评论深度分析平台。开源、自托管、零 API Key。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 简介

输入 Amazon ASIN 或上传评论 CSV → AI 自动完成 22 维度标签、用户画像识别、14 章洞察报告、交互式 HTML 看板。

**核心特点**：MIT 开源 / Docker 自托管 / 零 API Key（复用 Claude Code CLI）

## 项目结构

```
ReviewAnalyzer/
├── .env.example                  # 环境变量模板
├── CLAUDE.md                     # AI 编码助手规则
├── requirements.txt              # 汇总依赖
├── .memory-bank/                 # 📦 项目文档
│   ├── PRD.md                    #   产品需求文档
│   ├── tech_stack.md             #   技术选型
│   ├── implementation_plan.md    #   实施计划
│   ├── architecture.md           #   代码架构
│   └── progress.md               #   进度跟踪
└── review-analyzer-skill/        # 核心分析引擎
    ├── main.py                   #   CLI 入口（5 Phase 流程）
    ├── SKILL.md                  #   Claude Code Skill 定义
    ├── replay_phase2to5.py       #   快速重放（跳过数据获取）
    └── src/                      #   源码 + 模板 + 提示词
```

## 分析流程

```
Phase 1: 数据获取  →  Phase 2: AI 打标  →  Phase 3: 用户画像  →  Phase 4: 洞察报告  →  Phase 5: 输出看板
  (CSV/Sorftime)     (22维标签+并发)      (场景×性别交叉)       (14章+mermaid)       (6套主题HTML)
```

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/buluslan/review-analyzer.git
cd ReviewAnalyzer

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置（可选）
cp .env.example .env

# 4. 运行分析
cd review-analyzer-skill
python main.py your_reviews.csv --max-reviews 100
```

## 详细文档

| 文档 | 说明 |
|------|------|
| [PRD.md](.memory-bank/PRD.md) | 产品需求文档（功能、架构、里程碑） |
| [tech_stack.md](.memory-bank/tech_stack.md) | 技术选型与决策记录 |
| [implementation_plan.md](.memory-bank/implementation_plan.md) | 12 步实施计划 |
| [architecture.md](.memory-bank/architecture.md) | 代码架构与数据流 |
| [review-analyzer-skill/README.md](review-analyzer-skill/README.md) | 分析引擎详细文档 |

## 许可证

本项目采用 [MIT License](LICENSE) 开源。
