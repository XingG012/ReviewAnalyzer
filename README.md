# ReviewAnalyzer

多模块评论分析与数据洞察平台。

## 项目结构

```
ReviewAnalyzer/
├── .env.example              # 环境变量模板
├── .gitignore                # Git 忽略规则
├── LICENSE                   # MIT 许可证
├── README.md                 # 项目总览（本文件）
├── requirements.txt          # 汇总依赖
├── review-analyzer-skill/    # 模块1: AI 评论深度分析
│   ├── SKILL.md              # Claude Code Skill 定义
│   ├── README.md             # 模块详细文档
│   ├── main.py               # 入口
│   └── ...
└── (未来更多模块)
```

## 模块列表

### [review-analyzer-skill](review-analyzer-skill/)

AI 驱动的电商评论深度分析工具，Agent 原生架构。

- **22维度智能标签系统**: 人群/场景/功能/质量/服务/体验/市场/情感
- **14章深度洞察报告**: 从总览到行动仪表盘
- **6套主题可视化看板**: 玻璃拟态 + Chart.js 交互图表
- **多数据源**: 本地 CSV + Sorftime 平台
- **飞书同步**: 文档 + 白板图表

详见 [review-analyzer-skill/README.md](review-analyzer-skill/README.md)

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd ReviewAnalyzer

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 4. 进入模块目录使用
cd review-analyzer-skill
python main.py --help
```

## 环境配置

所有模块共享根目录的 `.env` 文件。首次使用时复制 `.env.example` 为 `.env` 并按需配置。

当前支持的配置项见 [.env.example](.env.example)。

## 许可证

本项目采用 [MIT License](LICENSE) 开源。
