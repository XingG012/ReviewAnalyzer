# Phase 1 实施计划 — Streamlit 验证期

> 版本: v1.0 | 日期: 2026-07-03 | 目标: 2-3 周
>
> 本计划基于 [PRD.md](PRD.md) §7 Phase 1 里程碑 和 [tech_stack.md](tech_stack.md) §4。
> 每个步骤描述"做什么"和"如何验证"，不包含具体代码。

---

## 总体目标

用 Streamlit 为现有 CLI 分析引擎包一层 Web UI，实现：
- 用户在浏览器中输入 ASIN / 上传 CSV → 点"开始分析"
- 实时看到 Phase 1→5 进度
- 完成后在线查看 HTML 看板 + MD 报告 + 下载所有产物

---

## 前置准备

- [ ] 确认 `review-analyzer-skill/` 现有模块可独立 import 且不报错
- [ ] 确认 Python 3.13+ 环境，安装 `streamlit` 和 `sqlite3`（Python 自带）
- [ ] 阅读 [PRD.md](PRD.md) §2.1-2.3 和 [CLAUDE.md](../CLAUDE.md) 的模块化规则

---

## Step 0: Amazon 爬虫集成

**目标**：从 GitHub 找到合适的开源 Amazon 评论爬虫，封装为 `data_fetchers/amazon_fetcher.py`，实现 ASIN → 评论数据的自动化获取。

**做什么**：

1. **搜索与评估开源爬虫**：
   - 在 GitHub 搜索 `amazon review scraper` / `amazon reviews crawler`
   - 评估标准：Star 数、最近更新时间、License（需 MIT/Apache/BSD 兼容）、是否支持多站点（US/UK/DE/JP）
   - 选 2-3 个候选，实际测试哪个最稳定

2. **创建 AmazonFetcher**：
   - 在 `review-analyzer-skill/src/data_fetchers/` 下创建 `amazon_fetcher.py`
   - 继承 `base.DataFetcher`，实现 4 个抽象方法（`fetch()` / `validate_config()` / `list_fields()` / `get_name()`）
   - `fetch(asin, fields, site)` 流程：验证 ASIN → 检查配置（代理、Cookie）→ 调用爬虫 → 标准化列名 → 保存为 CSV → 返回文件路径
   - `validate_config()` 检查：爬虫模块是否已安装、网络连通性、可选代理可用性

3. **反爬策略**：
   - User-Agent 轮换池（至少 10 个真实 UA）
   - 请求间隔控制（随机 3-8 秒）
   - 可选：代理 IP 池支持（通过环境变量 `PROXY_LIST` 配置）
   - 失败重试（单个 ASIN 最多重试 3 次，指数退避）

4. **标准化输出**：
   - 爬取的原始字段 → 标准字段映射（`body`, `rating`, `author`, `date`, `helpful_count`, `is_verified`, `images`）
   - 输出 CSV 使用 `utf-8-sig` 编码（与现有 `CsvFetcher` 输出格式一致）

5. **注册到 data_fetchers**：
   - 在 `data_fetchers/__init__.py` 中导出 `AmazonFetcher`
   - 在 `src/config.py` 中添加 `DATA_SOURCE: str = "amazon"` 选项

**验证方式**：
- 选一个公开 ASIN（如 `B08N5WRWNW`），运行 `fetch(asin="B08N5WRWNW", fields=[...], site="US")`
- 能成功获取至少 10 条评论，每条包含 `body`, `rating`, `author`, `date` 四个必选字段
- 连续 3 次调用不触发 Amazon 反爬封禁
- `validate_config()` 缺失依赖时返回 `False` 并给出明确提示
- 生成的 CSV 能被 `CsvFetcher` 正确解析（端到端兼容）
- 代码不超过 400 行，逻辑清晰，有完整的 docstring

---

## Step 1: 项目目录骨架

**目标**：创建 `streamlit_app/` 目录，建立可运行的空白 Streamlit 应用。

**做什么**：
1. 在项目根目录创建 `streamlit_app/` 文件夹
2. 创建 `streamlit_app/app.py`，写一个最简单的 Streamlit 页面：标题 `ReviewAnalyzer` + 一行说明文字
3. 创建 `streamlit_app/requirements.txt`，内容为 `streamlit>=1.40.0`
4. 运行 `streamlit run streamlit_app/app.py`，确认浏览器能打开

**验证方式**：
- `streamlit run streamlit_app/app.py` 启动不报错
- 浏览器打开 `http://localhost:8501` 能看到 "ReviewAnalyzer" 标题
- `import sys; sys.path.insert(0, '..'); from src.config import config` 不报 ImportError

---

## Step 2: UI 布局 — 三区结构

**目标**：搭建主页面三区布局框架（输入区 → 进度区 → 结果区），各区用占位文本即可。

**做什么**：
1. 使用 `st.sidebar` 放项目 Logo（文字即可）+ 导航说明
2. 主页从上到下分三个逻辑区：
   - **输入区**：ASIN 输入框（`st.text_input`）+ 站点下拉（`st.selectbox`）+ CSV 上传（`st.file_uploader`）+ "开始分析"按钮
   - **进度区**：空的占位容器（后续放进度条），初始隐藏
   - **结果区**：空的占位容器（后续放看板和报告），初始隐藏
3. 使用 `st.session_state` 管理页面状态（`state='input' | 'running' | 'done'`），控制各区显示/隐藏

**验证方式**：
- 页面渲染三区结构，输入框和按钮可交互
- 点击"开始分析"按钮（先不做任何事，只打印日志）不报错
- `st.session_state` 可以正确切换 `input → running → done` 三种状态

---

## Step 3: 输入校验与错误提示

**目标**：在点击"开始分析"之前，验证用户输入的有效性，给出清晰的错误提示。

**做什么**：
1. ASIN 输入框校验：非空、格式类似 `B0XXXXXXXXX`（10位字母数字），不合法时按钮旁显示红色提示
2. CSV 上传校验：文件扩展名 `.csv`，大小不超过 50MB
3. 站点下拉：US / UK / DE / JP，默认 US
4. 至少满足一项输入（ASIN 不为空 **或** 已上传 CSV），否则按钮禁用
5. 各校验失败时使用 `st.error()` 或 `st.warning()` 给出**中文**提示信息

**验证方式**：
- 空 ASIN + 未上传 CSV = 按钮禁用，鼠标悬停有提示
- 输入非法 ASIN 如 "abc123" = 红色提示 "ASIN 格式不正确"
- 上传非 CSV 文件（如 .jpg）= 提示 "请上传 CSV 文件"
- 既输入合法 ASIN 又上传 CSV = ASIN 优先（提示用户）

---

## Step 4: 分析引擎集成 — 端到端跑通

**目标**：点击"开始分析"后，实际调用现有 5 Phase 分析流程，在终端能看到完整输出。

**做什么**：
1. 在 `streamlit_app/` 下创建 `pipeline.py`，封装一个 `run_analysis()` 函数，接收参数：
   - `source`: `"csv"` 或 `"sorftime"`
   - `csv_file`: 上传的 CSV 文件路径（可为 None）
   - `asin`: 产品 ASIN（可为 None）
   - `max_reviews`: 分析数量上限
   - `template`: HTML 模板名（默认 `premium-gold`）
2. `run_analysis()` 内部依次调用现有模块：
   - `data_fetchers/` → 获取评论数据
   - `review_analyzer.py` → `analyze_all()` → 22 维打标
   - `user_persona_analyzer.py` → `analyze_user_personas()` → 画像
   - `insights_generator.py` → `generate_insights()` → 14 章报告
   - `output_manager.py` → `generate_outputs()` → MD + HTML + CSV
3. 返回一个 dict 包含所有产出文件路径和分析统计数据
4. 注意处理模块路径：`sys.path` 中需要加入 `review-analyzer-skill/` 目录

**验证方式**：
- 上传一个测试 CSV → 点"开始分析" → 终端能看到 Phase 1-5 的日志输出
- `run_analysis()` 返回的 dict 包含正确的文件路径
- 用 `python3 -c "from streamlit_app.pipeline import run_analysis"` 不报错
- 即使分析失败，函数也不会让整个 Streamlit 进程 crash（异常被捕获）

---

## Step 5: Phase 1 数据获取 — CSV 上传流程

**目标**：用户上传 CSV 后，系统正确解析并开始分析。

**做什么**：
1. 在 `pipeline.py` 中实现 CSV 上传流程：
   - 用户上传的文件保存到临时目录 `streamlit_app/data/uploads/`
   - 调用 `data_fetchers.csv_fetcher.CsvFetcher` 加载 CSV
   - 调用 `CsvFetcher.validate_config()` 检查文件可读性
   - 调用 `CsvFetcher.list_fields()` 获取支持的字段列表
2. 显示加载结果摘要：`共加载 X 条评论，评分范围 1-5 星`
3. 如果需要限制分析数量，在进入 Phase 2 打标前截取前 N 条

**验证方式**：
- 上传一个测试 CSV（至少 10 条评论）→ 显示加载条数
- 上传空 CSV 或格式错误文件 → 用户友好的中文错误提示，不 crash
- 上传 CSV 后 `st.session_state` 中保存了评论数据，可供后续 Phase 使用

---

## Step 6: 实时进度显示

**目标**：分析进行中，页面实时展示 Phase 1→5 的进度，让用户知道当前在干嘛。

**做什么**：
1. 使用 `st.progress()` 显示总体进度（0-100%），每个 Phase 占 20%
2. 使用 `st.status()` 显示当前 Phase 名称和详细状态
3. `pipeline.py` 的 `run_analysis()` 改为**生成器模式**（yield 进度事件），Streamlit 层轮询消费：
   - `yield {"phase": 1, "msg": "正在获取评论数据...", "pct": 10}`
   - `yield {"phase": 2, "msg": "已完成 45/100 条打标", "pct": 40}`
   - ...
4. 每个 Phase 状态用 emoji + 中文描述，如 `🧠 正在 AI 打标中... (47/100)`

**验证方式**：
- 点"开始分析"后，进度条从 0% 逐步走到 100%
- 能看到每个 Phase 的名称和描述在更新
- 打标阶段能看到 "已完成 X/总数" 的实时计数
- 分析完成后进度条正好 100%，状态显示 "✅ 分析完成"

---

## Step 7: 结果展示 — 看板在线预览

**目标**：分析完成后，HTML 看板直接在浏览器中展示，MD 报告渲染显示。

**做什么**：
1. 使用 `st.components.v1.html()` 内嵌展示生成的 HTML 看板：
   - 读取 Phase 5 生成的 HTML 文件内容
   - 设置合适的 `height` 参数（建议 2000px 或自适应）
2. 在页面左侧/顶部添加 Tab 切换：
   - **Tab 1: 可视化看板** → 内嵌 HTML
   - **Tab 2: 洞察报告** → 用 `st.markdown()` 渲染 MD 内容
   - **Tab 3: 打标数据预览** → 用 `st.dataframe()` 展示打标 CSV 前 100 行
3. 模板选择器：分析前可选 6 套主题（下拉框 + 缩略图描述），默认 `premium-gold`

**验证方式**：
- 分析完成后自动切换到结果区，能看到看板
- Tab 切换流畅，三栏内容都能正常显示
- MD 报告中的 Markdown 语法（标题、表格、列表）正确渲染
- 切换不同模板后重新生成，HTML 样式正确变化

---

## Step 8: 文件下载

**目标**：用户可一键下载分析产物的所有原始文件。

**做什么**：
1. 在结果区底部放下载按钮组：
   - **下载打标 CSV** — `st.download_button` + 读取 CSV 为 bytes
   - **下载洞察报告 MD** — 同上，MIME type `text/markdown`
   - **下载可视化看板 HTML** — 同上，MIME type `text/html`
2. 文件名格式：`{产品ASIN}_打标数据.csv` / `{ASIN}_洞察报告.md` / `{ASIN}_看板.html`
3. 也可以打包成 ZIP（可选，后续迭代）
4. 未生成的文件（如分析中途失败），对应按钮禁用并灰显

**验证方式**：
- 点击每个下载按钮，浏览器触发文件下载
- 下载的 CSV 能在 Excel / Google Sheets 中正常打开（UTF-8-BOM 编码）
- 下载的 HTML 用浏览器打开，样式和在线预览一致
- ASIN 为空时（纯 CSV 上传场景），文件名用时间戳代替 ASIN

---

## Step 9: 任务历史 — SQLite 持久化

**目标**：所有分析任务持久化到 SQLite，支持查看历史、重新打开结果。

**做什么**：
1. 创建 `streamlit_app/db.py`，封装 SQLite 操作：
   - 初始化：建表 `tasks`（字段见 [PRD.md](PRD.md) §3.3 的 `tasks` 表简化版：id, asin, status, created_at, output_dir, error_msg）
   - `save_task()` — 新建/更新任务记录
   - `list_tasks()` — 查询历史任务列表（按时间倒序，最近 50 条）
   - `get_task()` — 按 ID 获取单条任务
2. 侧边栏显示**历史任务列表**（最近 10 条），包含：
   - 状态图标（🟢 完成 / 🔵 运行中 / 🔴 失败）
   - ASIN 或文件名
   - 分析时间
3. 点击历史任务 → 加载该任务的输出目录 → 展示看板和报告（复用 Step 7 的展示逻辑）
4. 数据库文件存放在 `streamlit_app/data/tasks.db`

**验证方式**：
- 第一次使用自动创建 `tasks.db` 和 `tasks` 表
- 每次分析完成后，侧边栏历史列表自动新增一条记录
- 关闭浏览器重新打开，历史任务还在
- 点击历史任务，能重新看到当时的分析结果
- 并发分析两个任务，历史列表显示两条，各自状态独立

---

## Step 10: 错误处理与边界情况

**目标**：分析过程中任何环节出错，用户都能看到清晰的错误信息，且能重试。

**做什么**：
1. 为每个 Phase 的异常做分类处理：
   - **数据获取失败**（文件解析错误 / API 超时）→ 提示 "数据获取失败：{原因}，请检查文件格式或网络连接"
   - **AI 打标超时** → 提示 "打标超时，已完成的评论已保存，可减少分析数量后重试"
   - **CLI 不可用**（找不到 claude 命令）→ 提示 "未检测到 Claude Code CLI，请先安装：npm i -g @anthropic-ai/claude-code"
   - **磁盘空间不足** → 提示 "磁盘空间不足，请清理后重试"
2. 所有错误信息写入 SQLite（`error_msg` 字段），前端展示
3. 失败任务旁显示"重试"按钮，点击重新进入分析
4. 长时间无响应时（超过 30 分钟），显示"分析时间较长，请耐心等待" + 取消按钮
5. 处理空评论数据：上传的 CSV 没有任何评论记录时，提前拦截

**验证方式**：
- 上传格式损坏的 CSV → 友好错误提示，不显示 traceback
- 终端 `claude` 未安装 → 提示安装命令
- 手动中断分析后，任务状态正确保存为"失败"，可以重试
- 提交 0 条评论的 CSV → 提示"文件中没有找到有效评论"

---

## Step 11: Docker 部署

**目标**：其他用户可以通过 `docker compose up` 一键启动。

**做什么**：
1. 创建 `streamlit_app/Dockerfile`：
   - 基于 `python:3.13-slim`
   - 复制 `review-analyzer-skill/` 和 `streamlit_app/` 到容器
   - 安装依赖：`review-analyzer-skill/requirements.txt` + `streamlit`
   - EXPOSE 8501
   - CMD `streamlit run app.py --server.address=0.0.0.0`
2. 在项目根目录创建 `docker-compose.yml`：
   ```yaml
   services:
     app:
       build:
         context: .
         dockerfile: streamlit_app/Dockerfile
       ports:
         - "8501:8501"
       volumes:
         - ./output:/app/output          # 分析结果持久化
         - ./streamlit_app/data:/app/data  # SQLite 持久化
   ```
3. 在 `README.md` 中写清楚启动命令：
   ```bash
   git clone https://github.com/buluslan/review-analyzer.git
   cd review-analyzer
   docker compose up -d
   # 打开 http://localhost:8501
   ```

**验证方式**：
- `docker compose up` 启动不报错
- 浏览器访问 `localhost:8501` 能看到完整的 Web UI
- 上传 CSV 文件并完成完整分析流程
- `docker compose down` 后重新 `up`，历史任务还在（SQLite volume 持久化生效）

---

## Step 12: 文档与发布

**目标**：GitHub README 更新，准备对外发布。

**做什么**：
1. 更新 `README.md`：
   - 顶部 Badge（MIT license / Docker pulls / GitHub stars）
   - 一句话介绍 + 功能截图
   - 快速开始（Docker 和 本地开发 两种方式）
   - 输入方式说明（CSV 上传 / Sorftime API）
   - 5 Phase 流程简介
   - 输出产物列表
   - 技术栈说明（链接到 tech_stack.md）
   - 贡献指南链接
2. 录一个 30 秒的演示 GIF（ASIN 输入 → 进度 → 看板展示）
3. 在 GitHub 上打 tag `v1.0.0-streamlit`，写 Release Notes
4. 确保 `.gitignore` 包含 `streamlit_app/data/*.db`、`output/`、`*.pyc`、`.venv/`

**验证方式**：
- 新 clone 仓库后，按照 README 的步骤能成功跑起来
- Release 页面能看到完整的功能描述和下载链接
- Docker 镜像能正常拉取和启动

---

## 进度跟踪

| Step | 状态 | 开始 | 完成 | 备注 |
|------|------|------|------|------|
| 0. Amazon 爬虫集成 | ⬜ 待开始 | | | |
| 1. 目录骨架 | ⬜ 待开始 | | | |
| 2. UI 三区布局 | ⬜ 待开始 | | | |
| 3. 输入校验 | ⬜ 待开始 | | | |
| 4. 分析引擎集成 | ⬜ 待开始 | | | |
| 5. CSV 上传流程 | ⬜ 待开始 | | | |
| 6. 实时进度 | ⬜ 待开始 | | | |
| 7. 结果展示 | ⬜ 待开始 | | | |
| 8. 文件下载 | ⬜ 待开始 | | | |
| 9. 任务历史 | ⬜ 待开始 | | | |
| 10. 错误处理 | ⬜ 待开始 | | | |
| 11. Docker 部署 | ⬜ 待开始 | | | |
| 12. 文档与发布 | ⬜ 待开始 | | |

---

## 不在此阶段的范围（Phase 2 再做）

- ❌ 用户注册/登录（Phase 1 无用户系统）
- ❌ React / Next.js 前端重写
- ❌ Celery 任务队列
- ❌ PostgreSQL / Redis / MinIO
- ❌ SSE 实时推送（Phase 1 用 st.progress 即可）
- ❌ PDF 导出
- ❌ 分享链接
