"""ReviewAnalyzer — 电商评论深度分析平台"""

import os
import re
import sys
from pathlib import Path

import streamlit as st

# ── 模块路径 ────────────────────────────────────────────────
_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "review-analyzer-skill"
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from src.data_fetchers.csv_fetcher import CsvFetcher  # noqa: E402
from src.data_loader import load_reviews_from_file            # noqa: E402
from pipeline import run_analysis                             # noqa: E402

# ── 上传目录 ────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).resolve().parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── 页面配置 ────────────────────────────────────────────────
st.set_page_config(
    page_title="ReviewAnalyzer",
    page_icon="📊",
    layout="wide",
)

# ── 侧边栏 ──────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 ReviewAnalyzer")
    st.caption("电商评论深度分析")
    st.divider()
    st.markdown("**数据来源**：CSV 上传 / Sorftime API")
    st.markdown("**分析流程**：5 Phase 流水线")
    st.markdown("**输出**：MD 报告 + HTML 看板 + 数据下载")

# ── 初始化 session_state ────────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = "input"

# ── 输入区 ──────────────────────────────────────────────────
if st.session_state.state == "input":
    st.header("🔍 开始新的分析")

    col1, col2 = st.columns(2)
    with col1:
        asin = st.text_input(
            "ASIN（商品编号）",
            placeholder="例如：B0DGV4T6BK",
            key="asin",
        )
    with col2:
        site = st.selectbox("站点", options=["US", "UK", "DE", "JP"], key="site")

    uploaded_file = st.file_uploader(
        "或上传评论 CSV 文件",
        type=["csv"],
        key="uploaded_file",
    )

    # ── 校验逻辑 ──────────────────────────────────────────
    asin_valid = False
    csv_valid = False
    csv_preview = None

    # ASIN 校验
    if asin:
        if re.match(r"^[A-Z0-9]{10}$", asin.strip().upper()):
            asin_valid = True
        else:
            st.error("ASIN 格式不正确，应为 10 位字母数字组合（如 B0DGV4T6BK）")

    # CSV 校验 + 预览
    if uploaded_file is not None:
        if not uploaded_file.name.lower().endswith(".csv"):
            st.error("请上传 CSV 格式的文件")
        elif uploaded_file.size > 50 * 1024 * 1024:
            st.error("文件大小不能超过 50MB")
        else:
            # 保存 + CsvFetcher 校验
            csv_path = UPLOAD_DIR / uploaded_file.name
            with open(csv_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            fetcher = CsvFetcher({"file_path": str(csv_path)})
            if fetcher.validate_config():
                csv_valid = True
                st.session_state.running_csv_path = str(csv_path)
                # 预览摘要：用 load_reviews_from_file 加载并校验
                try:
                    reviews, df = load_reviews_from_file(str(csv_path))
                    st.success(
                        f"共加载 **{len(reviews)}** 条评论，"
                        f"评分范围 {df['rating'].min():.0f}-{df['rating'].max():.0f} 星"
                    )
                except Exception as e:
                    st.error(f"CSV 文件解析失败：{e}")
            else:
                st.error("CSV 文件格式无法识别，请检查文件内容")

    # 同时有 ASIN 和 CSV 时，ASIN 优先
    if asin_valid and csv_valid:
        st.info(f"检测到 ASIN 和 CSV 文件，将优先使用 ASIN ({asin.strip().upper()})")

    can_start = asin_valid or csv_valid

    if st.button(
        "🚀 开始分析",
        type="primary",
        use_container_width=True,
        disabled=not can_start,
    ):
        st.session_state.state = "running"
        st.session_state.running_asin = asin.strip().upper() if asin_valid else "UNKNOWN"
        st.rerun()

# ── 进度区 ──────────────────────────────────────────────────
elif st.session_state.state == "running":
    st.header("⏳ 分析进行中...")

    csv_path = st.session_state.get("running_csv_path", "")
    asin = st.session_state.get("running_asin", "UNKNOWN")

    if not csv_path:
        csv_path = os.path.abspath(
            os.path.join(
                _ENGINE_ROOT, "examples", "reviews_sample.csv"
            )
        )

    with st.spinner("正在分析，约需 3-5 分钟..."):
        result = run_analysis(
            csv_path=csv_path,
            asin=asin,
            max_reviews=100,
            template="premium-gold",
        )

    st.session_state.analysis_result = result
    st.session_state.state = "done"
    st.rerun()

# ── 结果区 ──────────────────────────────────────────────────
elif st.session_state.state == "done":
    result = st.session_state.get("analysis_result", {})

    if result.get("success"):
        st.header("✅ 分析完成")
        st.success(
            f"{result['total_reviews']} 条评论 · "
            f"{result['persona_count']} 个画像"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 评论数", result["total_reviews"])
        with col2:
            st.metric("👥 用户画像", result["persona_count"])
        with col3:
            st.metric("✅ 状态", "完成" if result["success"] else "失败")

        st.info("看板和报告将在 Step 7 中展示（目前为文本提示）")
        if result.get("md_path"):
            st.caption(f"MD 报告: {result['md_path']}")
        if result.get("html_path"):
            st.caption(f"HTML 看板: {result['html_path']}")
    else:
        st.header("❌ 分析失败")
        st.error(result.get("error", "未知错误"))
        st.caption("请检查 CSV 文件格式或检查 Claude Code CLI 是否可用")

    if st.button("🔄 开始新分析"):
        for key in [
            "state", "analysis_result", "running_csv_path", "running_asin",
        ]:
            st.session_state.pop(key, None)
        st.session_state.state = "input"
        st.rerun()
