"""ReviewAnalyzer — 电商评论深度分析平台"""

import html
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
from pipeline import run_analysis_with_progress               # noqa: E402
from db import save_task, list_tasks, get_task, save_upload, list_uploads, delete_upload  # noqa: E402

# ── 上传目录 ────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).resolve().parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _render_markdown_with_mermaid(md_content: str) -> None:
    """渲染含 Mermaid 图表的 Markdown"""
    # 分割内容：mermaid 块和普通文本交替
    parts = re.split(r"(```mermaid\s*\n.*?```)", md_content, flags=re.DOTALL)

    mermaid_cdn = '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'
    mermaid_init = '<script>mermaid.initialize({startOnLoad:true,securityLevel:"loose",logLevel:"error"});</script>'

    for i, part in enumerate(parts):
        m_match = re.match(r"```mermaid\s*\n(.*?)```", part, re.DOTALL)
        if m_match:
            diagram = html.escape(m_match.group(1), quote=False)
            full = f"""<!DOCTYPE html><html><head>{mermaid_cdn}{mermaid_init}</head><body>
<pre class="mermaid">{diagram}</pre></body></html>"""
            st.components.v1.html(full, height=450, scrolling=True)  # type: ignore[attr-defined]
        elif part.strip():
            st.markdown(part.strip())

# ── 页面配置 ────────────────────────────────────────────────
st.set_page_config(
    page_title="ReviewAnalyzer",
    page_icon="📊",
    layout="wide",
)

# ── 初始化 session_state ────────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = "input"
if "show_history" not in st.session_state:
    st.session_state.show_history = False
if "upload_saved_for" not in st.session_state:
    st.session_state.upload_saved_for = None
if "sidebar_view" not in st.session_state:
    st.session_state.sidebar_view = None

# ── 侧边栏 ──────────────────────────────────────────────────
is_running = st.session_state.state == "running"
with st.sidebar:
    st.title("📊 ReviewAnalyzer")
    st.divider()

    # ── 1. 开始分析 ──────────────────────────────────────
    with st.expander("🆕 开始分析", expanded=st.session_state.state == "input"):
        if is_running:
            # 分析中：显示当前进度，点击返回
            st.info("⏳ 正在分析...")
            if st.button("📊 查看进度", use_container_width=True, type="primary"):
                st.session_state.sidebar_view = None
                st.rerun()
        else:
            if st.button("新建分析任务", use_container_width=True,
                         type="primary" if st.session_state.state != "input" else "secondary"):
                for key in ["state", "analysis_result", "running_csv_path",
                             "running_asin", "task_id", "sidebar_view"]:
                    st.session_state.pop(key, None)
                st.session_state.state = "input"
                st.rerun()

    # ── 2. 已上传文件 ─────────────────────────────────────
    with st.expander("📁 已上传文件", expanded=st.session_state.get("show_files", False)):
        st.session_state.show_files = True
        files = list_uploads(limit=20)
        if files:
            for f in files:
                reviews = f.get("review_count", 0)
                size_kb = f.get("size_bytes", 0) / 1024
                label = f"📄 {f['original_name']} ({reviews}条 · {size_kb:.0f}KB)"
                if st.button(label, key=f"file_{f['id']}", use_container_width=True):
                    if is_running:
                        st.session_state.sidebar_view = ("file_preview", f["id"])
                    else:
                        st.session_state.state = "file_preview"
                        st.session_state.preview_file = f
                    st.rerun()
        else:
            st.caption("暂无上传文件")

    st.divider()

    # ── 3. 历史分析 ───────────────────────────────────────
    with st.expander("📋 历史分析", expanded=st.session_state.get("show_hist_expand", False)):
        st.session_state.show_hist_expand = True
        tasks = [t for t in list_tasks(limit=20) if t["status"] in ("done", "failed")]
        if tasks:
            status_icons = {"done": "🟢", "failed": "🔴"}
            for t in tasks:
                icon = status_icons.get(t["status"], "⚪")
                created = t["created_at"][:16].replace("T", " ")
                reviews = t.get("total_reviews", 0)
                personas = t.get("persona_count", 0)
                label = f"{icon} {t['asin']} · {reviews}条 · {personas}画像"
                if st.button(label, key=f"hist_{t['id']}", use_container_width=True):
                    if is_running:
                        st.session_state.sidebar_view = ("history", t["id"])
                    else:
                        st.session_state.state = "history"
                        st.session_state.history_task = t
                    st.rerun()
        else:
            st.caption("暂无已完成的分析")
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

    # 模板选择（卡片式预览）
    st.write("**可视化看板主题**")
    THEME_INFO = {
        "premium-gold":     ("🥇 Premium Gold",   "黑金奢华 · Playfair Display",      "高管汇报、品牌展示",     "#1a1a2e,#d4af37"),
        "dark-tech":        ("🌃 Dark Tech",       "赛博朋克 · Cyan + 毛玻璃",         "技术团队、数据密集",     "#0d1117,#00d4ff"),
        "linear-minimal":   ("📐 Linear Minimal",  "极简白蓝 · 清透玻璃",              "产品评审、简洁汇报",     "#fafafa,#5e6ad2"),
        "posthog-analytics":("🦔 PostHog",         "暖白橙色 · 暖色玻璃",              "运营复盘、增长分析",     "#fef9ef,#f96132"),
        "stripe-executive": ("💳 Stripe Executive","翡翠绿 · 金融企业风",              "金融报告、投资决策",     "#f6f9fc,#00d924"),
        "warm-editorial":   ("📰 Warm Editorial",  "纸色铜色 · 编辑风格",              "品牌报告、阅读分享",     "#faf8f5,#b76e2e"),
    }
    if "selected_template" not in st.session_state:
        st.session_state.selected_template = "premium-gold"

    cols = st.columns(3)
    for i, (key, (title, desc, use_case, colors)) in enumerate(THEME_INFO.items()):
        c1, c2 = colors.split(",")
        with cols[i % 3]:
            selected = st.session_state.selected_template == key
            border = f"3px solid {c2}" if selected else f"1px solid {c1}"
            bg = f"linear-gradient(135deg, {c1} 0%, {c2} 100%)"
            opacity = "1" if selected else "0.65"
            text_color = "#fff"
            card_html = f"""
            <div style="border:{border};border-radius:12px;padding:14px;margin:4px 0;
                        background:{bg};color:{text_color};min-height:110px;opacity:{opacity};">
                <div style="font-weight:700;font-size:15px;">{title}</div>
                <div style="font-size:12px;margin:6px 0;opacity:0.9;">🎨 {desc}</div>
                <div style="font-size:11px;opacity:0.75;">💼 {use_case}</div>
                {f'<div style="margin-top:6px;font-size:13px;">⭐ 当前选择</div>' if selected else ''}
            </div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button("选择" if not selected else "★ 已选", key=f"theme_{key}",
                         use_container_width=True,
                         type="primary" if not selected else "secondary"):
                st.session_state.selected_template = key
                st.rerun()

    template = st.session_state.selected_template

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
                    # 防重复：同一个文件只存一次
                    if st.session_state.upload_saved_for != uploaded_file.name:
                        save_upload(
                            original_name=uploaded_file.name,
                            stored_path=str(csv_path),
                            size_bytes=uploaded_file.size,
                            review_count=len(reviews),
                        )
                        st.session_state.upload_saved_for = uploaded_file.name
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
        st.session_state.running_template = template

        # 空数据拦截
        if csv_valid:
            try:
                revs, _ = load_reviews_from_file(st.session_state.running_csv_path)
                if len(revs) == 0:
                    st.error("文件中没有找到有效评论，请检查 CSV 格式")
                    st.rerun()
            except Exception as e:
                st.error(f"CSV 解析失败：{e}")
                st.rerun()

        # 创建任务记录
        st.session_state.task_id = save_task(
            asin=st.session_state.running_asin,
            status="running",
        )
        st.rerun()

# ── 进度区 ──────────────────────────────────────────────────
elif st.session_state.state == "running":
    # 如果侧边栏选了文件/历史，嵌入视图
    sidebar_view = st.session_state.get("sidebar_view")
    if sidebar_view:
        view_type, view_id = sidebar_view
        if view_type == "file_preview":
            from db import get_upload
            f = get_upload(view_id)
            if f:
                st.subheader(f"📄 {f.get('original_name', '')}")
                if os.path.exists(f["stored_path"]):
                    import pandas as pd
                    df = pd.read_csv(f["stored_path"])
                    st.dataframe(df, use_container_width=True, height=400)
    elif sidebar_view is False:
        pass  # explicitly cleared

    st.header("⏳ 分析进行中...")

    csv_path = st.session_state.get("running_csv_path", "")
    asin = st.session_state.get("running_asin", "UNKNOWN")

    if not csv_path:
        csv_path = os.path.abspath(
            os.path.join(
                _ENGINE_ROOT, "examples", "reviews_sample.csv"
            )
        )

    # 进度条 + 状态容器
    progress_bar = st.progress(0, text="0%")
    status_placeholder = st.empty()

    # 遍历生成器，实时更新进度
    for event in run_analysis_with_progress(
        csv_path=csv_path,
        asin=asin,
        max_reviews=100,
        template=st.session_state.get("running_template", "premium-gold"),
    ):
        pct = event.get("pct", 0)
        msg = event.get("msg", "")
        progress_bar.progress(pct, text=f"{pct}%")

        phase = event.get("phase", 0)
        if phase > 0:
            status_placeholder.info(f"**Phase {phase}/5** — {msg}")
        else:
            status_placeholder.error(msg)

        if event.get("done"):
            st.session_state.analysis_result = event.get("result", {})
            st.session_state.state = "done"
            st.rerun()

# ── 结果区 ──────────────────────────────────────────────────
elif st.session_state.state == "done":
    result = st.session_state.get("analysis_result", {})

    if result.get("success"):
        st.header("✅ 分析完成")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 评论数", result["total_reviews"])
        with col2:
            st.metric("👥 用户画像", result["persona_count"])
        with col3:
            st.metric("✅ 状态", "完成")

        st.divider()

        tab1, tab2, tab3 = st.tabs(["📊 可视化看板", "📝 洞察报告", "📋 打标数据"])

        with tab1:
            html_path = result.get("html_path", "")
            if html_path and os.path.exists(html_path):
                with open(html_path, encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=1200, scrolling=True)  # type: ignore[attr-defined]
            else:
                st.warning("HTML 看板未生成")

        with tab2:
            md_path = result.get("md_path", "")
            if md_path and os.path.exists(md_path):
                with open(md_path, encoding="utf-8") as f:
                    _render_markdown_with_mermaid(f.read())
            else:
                st.warning("洞察报告未生成")

        with tab3:
            csv_path = result.get("csv_out_path", "")
            if csv_path and os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)
                st.dataframe(df.head(100), use_container_width=True)
            else:
                st.warning("打标数据未生成")
    else:
        st.header("❌ 分析失败")
        st.error(result.get("error", "未知错误"))
        st.caption("请检查 CSV 文件格式或检查 Claude Code CLI 是否可用")
        col1, _ = st.columns([1, 3])
        with col1:
            if st.button("🔄 重试分析", use_container_width=True):
                st.session_state.state = "running"
                st.rerun()

    # ── 更新任务记录 ──────────────────────────────────────
    task_id = st.session_state.get("task_id", "")
    if task_id and result.get("success"):
        save_task(
            task_id=task_id,
            asin=st.session_state.get("running_asin", "UNKNOWN"),
            status="done",
            output_dir=os.path.dirname(result.get("md_path", "")),
            total_reviews=result.get("total_reviews", 0),
            persona_count=result.get("persona_count", 0),
        )
    elif task_id:
        save_task(
            task_id=task_id,
            status="failed",
            error_msg=result.get("error", ""),
        )

    # ── 文件下载 ──────────────────────────────────────────
    if result.get("success"):
        st.divider()
        st.subheader("📥 下载分析产物")
        asin = st.session_state.get("running_asin", "UNKNOWN")

        col1, col2, col3 = st.columns(3)

        with col1:
            csv_path = result.get("csv_out_path", "")
            if csv_path and os.path.exists(csv_path):
                with open(csv_path, "rb") as f:
                    st.download_button(
                        f"📋 打标 CSV",
                        data=f,
                        file_name=f"{asin}_打标数据.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
            else:
                st.button("📋 打标 CSV", disabled=True, use_container_width=True)

        with col2:
            md_path = result.get("md_path", "")
            if md_path and os.path.exists(md_path):
                with open(md_path, "rb") as f:
                    st.download_button(
                        f"📝 洞察报告 MD",
                        data=f,
                        file_name=f"{asin}_洞察报告.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
            else:
                st.button("📝 洞察报告 MD", disabled=True, use_container_width=True)

        with col3:
            html_path = result.get("html_path", "")
            if html_path and os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    st.download_button(
                        f"📊 可视化看板 HTML",
                        data=f,
                        file_name=f"{asin}_看板.html",
                        mime="text/html",
                        use_container_width=True,
                    )
            else:
                st.button("📊 可视化看板 HTML", disabled=True, use_container_width=True)

    st.divider()
    if st.button("🔄 开始新分析", use_container_width=True):
        for key in [
            "state", "analysis_result", "running_csv_path", "running_asin",
            "task_id",
        ]:
            st.session_state.pop(key, None)
        st.session_state.state = "input"
        st.rerun()

# ── 文件预览区 ──────────────────────────────────────────────
elif st.session_state.state == "file_preview":
    f = st.session_state.get("preview_file", {})
    st.header(f"📄 {f.get('original_name', '未知文件')}")
    st.caption(f"上传时间: {f.get('created_at', '')[:16].replace('T', ' ')} · "
               f"{f.get('review_count', 0)} 条评论 · "
               f"{f.get('size_bytes', 0) / 1024:.0f} KB")

    path = f.get("stored_path", "")
    if path and os.path.exists(path):
        import pandas as pd
        df = pd.read_csv(path)
        st.dataframe(df, use_container_width=True, height=500)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if st.button("🚀 分析此文件", use_container_width=True, type="primary"):
                st.session_state.state = "running"
                st.session_state.running_csv_path = path
                st.session_state.running_asin = "UNKNOWN"
                st.session_state.task_id = save_task(
                    asin=f.get("original_name", "UNKNOWN"),
                    status="running",
                )
                st.rerun()
        with col_f2:
            if st.button("🗑️ 删除此文件", use_container_width=True):
                delete_upload(f["id"])
                st.session_state.state = "input"
                st.rerun()
    else:
        st.warning("文件已被删除")

    if st.button("🔄 返回首页", use_container_width=True):
        st.session_state.state = "input"
        st.rerun()

# ── 历史任务区 ──────────────────────────────────────────────
elif st.session_state.state == "history":
    t = st.session_state.get("history_task", {})
    st.header(f"📋 历史分析: {t.get('asin', 'N/A')}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("状态", {"done": "✅ 完成", "failed": "❌ 失败", "running": "⏳ 运行中"}.get(t.get("status", ""), t.get("status", "")))
    with col2:
        st.metric("评论数", t.get("total_reviews", 0))

    output_dir = t.get("output_dir", "")
    if output_dir and os.path.isdir(output_dir):
        files = sorted(os.listdir(output_dir))
        for f in files:
            path = os.path.join(output_dir, f)
            if f.endswith(".csv") and "打标" in f:
                st.subheader("📋 打标数据")
                import pandas as pd
                st.dataframe(pd.read_csv(path).head(100), use_container_width=True)
            elif f.endswith(".md") and "洞察" in f:
                st.subheader("📝 洞察报告")
                with open(path, encoding="utf-8") as fh:
                    st.markdown(fh.read())
            elif f.endswith(".html") and "可视化" in f:
                st.subheader("📊 可视化看板")
                with open(path, encoding="utf-8") as fh:
                    st.components.v1.html(fh.read(), height=1200, scrolling=True)  # type: ignore[attr-defined]
    else:
        st.warning("该任务的输出文件已不存在")

    if st.button("🔄 开始新分析", use_container_width=True):
        st.session_state.state = "input"
        st.rerun()
