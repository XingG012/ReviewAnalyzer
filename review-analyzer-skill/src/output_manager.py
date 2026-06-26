"""
输出管理器 V2.0（Phase 4 的核心）

统一管理所有输出通道：
- MD 洞察报告（始终生成）
- HTML 可视化看板（生成，除非用户传 template_name=None）
- 飞书同步（可选：文档 + 画板图表）

调用关系：
main.py → generate_outputs() → _build_md_content()   (写 MD)
                              → _write_html_dashboard() (渲染 HTML)
                              → feishu_sync.sync_report() (可选飞书)
"""

import json                                                             # JSON 处理
import logging                                                          # 日志
from pathlib import Path                                                # 文件路径
from typing import Any, Dict, List, Optional                            # 类型注解

from src.config import config                                           # 全局配置
from src.chart_engine import ChartConfig, generate_all_charts            # 图表引擎：生成 8 类 Chart.js 配置
from src.template_engine import list_templates, render                   # 模板引擎：渲染 HTML 看板

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Markdown 报告生成
# ---------------------------------------------------------------------------

def _build_md_content(analysis_data: dict, creator: str, asin: str) -> str:
    """
    构建 Markdown 报告正文（纯 Python 拼接，不调 AI）

    把 analysis_data 里的统计、画像、洞察等数据拼成一篇完整的 MD 报告。
    支持两种格式：
    - 新版: analysis_data["chapters"] 是结构化的章节列表（直接遍历）
    - 旧版: 从散装字段组装（情感分布、高频标签、画像、洞察正文）

    Args:
        analysis_data: main.py 组装的分析结果字典
        creator: 报告署名
        asin: 产品 ASIN

    Returns:
        Markdown 格式的完整报告字符串
    """
    from datetime import datetime                                       # 运行时导入

    product_name = analysis_data.get("product_name", asin)               # 产品名（默认用 ASIN）
    summary = analysis_data.get("summary", {})                           # 统计摘要 {"total": 100, "tagged": 95}
    sentiment = analysis_data.get("sentiment", analysis_data.get("sentiment_distribution", {}))  # 情感分布
    top_tags = analysis_data.get("top_tags", {})                         # 高频标签
    personas = analysis_data.get("personas", [])                         # 用户画像列表
    insights_md = analysis_data.get("insights_md", analysis_data.get("report", ""))  # Phase 3 生成的洞察正文
    chapters = analysis_data.get("chapters", [])                         # 新版结构化章节
    statistics = analysis_data.get("statistics", {})                     # 统计数据

    # ── 报告头部 ──
    lines: List[str] = [
        f"# {product_name} 评论深度分析报告",                             # 一级标题
        "",
        f"> 分析工具: Review Analyzer Skill V2.0",                        # 引用块：工具信息
        f"> 署名: {creator}",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 评论数: {summary.get('total', analysis_data.get('total_reviews', 'N/A'))}",
        "",
        "---",                                                            # 水平分割线
        "",
    ]

    # ── 新版格式：有结构化 chapters 就直接遍历 ──
    if chapters:
        for chapter in chapters:
            title = chapter.get("title", "")
            content = chapter.get("content", "")
            if title and content:
                lines.append(f"## {title}\n\n{content}\n\n")              # 二级标题 + 内容
    else:
        # ── 旧版格式：从散装字段组装 ──
        # 情感分布
        if sentiment:
            lines.append("## 情感分布\n")
            total = summary.get("total", 0)
            for label, count in sentiment.items():                       # 如 "强烈推荐": 45, "中立": 12, ...
                pct = (count / total * 100) if total > 0 else 0
                lines.append(f"- **{label}**: {count} 条 ({pct:.1f}%)")
            lines.append("")

        # 高频标签 Top 20
        if top_tags:
            lines.append("## 高频标签\n")
            for i, (tag, count) in enumerate(list(top_tags.items())[:20], 1):
                lines.append(f"{i}. **{tag}**: {count} 次")
            lines.append("")

        # 用户画像
        if personas:
            lines.append("## 用户画像\n")
            for persona in personas:
                name = persona.get("name", "未知画像")
                count = persona.get("count", 0)
                lines.append(f"### {name} ({count} 条)\n")               # 三级标题：画像名 + 人数
                tags = persona.get("tags", {})
                for k, v in tags.items():                                 # 遍历该画像的标签特征
                    if v and v not in ("未提及", "不明", "无", ""):      # 过滤噪声标签
                        lines.append(f"- {k}: {v}")
                lines.append("")

        # 洞察正文（Phase 3 AI 生成的 Markdown 原文）
        if insights_md:
            lines.append("## 深度洞察\n")
            lines.append(insights_md)
            lines.append("")

    # 统计数据附录
    if statistics:
        lines.append("## 数据统计\n")
        for key, value in statistics.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML 看板生成
# ---------------------------------------------------------------------------

def _write_html_dashboard(
    html_path: Path,
    analysis_data: dict,
    chart_configs: List[ChartConfig],
    template_name: str,
    asin: str,
    creator: str,
) -> None:
    """
    写入 HTML 可视化看板

    调用 template_engine.render() 渲染选定的主题模板，
    注入分析数据和图表配置。渲染失败时写入一个简单的错误页面降级。

    Args:
        html_path: 输出 HTML 文件路径
        analysis_data: 分析结果数据
        chart_configs: chart_engine 生成的 8 类图表配置
        template_name: 模板名（如 "premium-gold"）
        asin: 产品码
        creator: 署名
    """
    # 构建注入数据（确保 asin 和 creator 一定存在）
    injection_data = dict(analysis_data)                                 # 浅拷贝避免污染原数据
    injection_data.setdefault("asin", asin)                              # 没有 asin 就补充
    injection_data.setdefault("creator", creator)                        # 没有 creator 就补充

    try:
        html_content = render(template_name, injection_data, chart_configs)  # Jinja2 渲染 HTML
        html_path.write_text(html_content, encoding="utf-8")              # 写入文件
    except Exception as exc:                                               # 渲染失败，降级
        logger.error("HTML 看板渲染失败: %s", exc)
        # 写一个极简的错误页面（至少文件存在，不丢结果）
        html_path.write_text(
            f"<html><body><h1>看板生成失败</h1><p>{exc}</p></body></html>",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# 模板选择
# ---------------------------------------------------------------------------

def select_template() -> str:
    """
    交互式模板选择（终端模式使用）

    逻辑：
    - 0 个模板 → 返回默认 "premium-gold"
    - 1 个模板 → 自动选择
    - ≥2 个模板 → 列出所有让用户选（输入编号）

    Returns:
        模板名称字符串
    """
    templates = list_templates()                                         # 扫描 templates/ 目录

    if not templates:                                                     # 没有模板文件
        logger.warning("未发现任何模板，使用默认模板名称 'premium-gold'")
        return "premium-gold"

    if len(templates) == 1:                                               # 只有一个模板 → 不用选了
        name = templates[0]["name"]
        logger.info("仅有一个模板，自动选择: %s", name)
        return name

    # 交互式选择（多个模板）
    print("\n可用模板列表:")
    for i, tpl in enumerate(templates, 1):
        desc = tpl.get("description", "")
        print(f"  {i}. {tpl['name']} - {desc}")

    print(f"\n  输入编号选择（默认 1）: ", end="")

    try:
        choice = input().strip()
        if not choice:                                                    # 直接回车 → 选第一个
            return templates[0]["name"]
        idx = int(choice) - 1                                             # 转成 0-based 索引
        if 0 <= idx < len(templates):                                     # 范围检查
            return templates[idx]["name"]
    except (ValueError, EOFError):                                        # 输入非数字或 EOF
        pass

    return templates[0]["name"]                                           # 异常默认选第一个


# ---------------------------------------------------------------------------
# 核心接口 — 函数式 API（推荐使用）
# ---------------------------------------------------------------------------

def generate_outputs(
    analysis_data: dict,
    output_config: Optional[dict] = None,
) -> dict:
    """
    编排所有输出通道，生成完整报告（Phase 4 的入口函数）

    执行步骤：
    1. 生成图表配置（chart_engine.generate_all_charts）
    2. 生成 Markdown 报告（_build_md_content）
    3. 生成 HTML 看板（_write_html_dashboard）
    4. 可选飞书同步（feishu_sync.sync_report）

    每个步骤独立 try-except，某一步失败不影响其他步骤。

    Args:
        analysis_data: main.py 组装的完整分析结果
        output_config: 输出配置，可选键:
            - template_name (str): 模板名，None=跳过 HTML
            - sync_feishu (bool): 是否同步飞书
            - output_dir (str): 自定义输出目录
            - asin (str): 产品码
            - creator (str): 报告署名

    Returns:
        {
            "md_path": str,             # MD 报告路径
            "html_path": str,           # HTML 看板路径（可能为空）
            "feishu_result": dict,      # 飞书同步结果
            "charts": list,             # ChartConfig 序列化列表
        }
    """
    if output_config is None:
        output_config = {}

    # ── 提取参数 ──
    asin = output_config.get("asin") or analysis_data.get("asin", "unknown")
    creator = output_config.get("creator", analysis_data.get("creator", "AI Assistant"))

    # ── 确定输出目录 ──
    output_dir_str = output_config.get("output_dir")
    if output_dir_str:
        output_dir = Path(output_dir_str)                                 # 自定义目录
    else:
        output_dir = config.OUTPUT_DIR                                    # 默认目录（output/ 或环境变量）

    # ── 初始化返回值 ──
    result: Dict[str, Any] = {
        "md_path": "",
        "html_path": "",
        "feishu_result": {                                                # 飞书结果默认值
            "success": False,
            "doc_url": "",
            "whiteboard_urls": [],
            "whiteboard_count": 0,
            "error": "未执行飞书同步",
        },
        "charts": [],
    }

    logger.info("开始生成输出: ASIN=%s, output_dir=%s", asin, output_dir)

    # Step 1: 生成图表配置（8 类图表：饼图/柱状图/雷达图/热力图等）
    try:
        chart_configs = generate_all_charts(analysis_data)                # 调用 chart_engine
        result["charts"] = [cc.to_dict() for cc in chart_configs]         # ChartConfig → dict 序列化
        logger.info("图表配置生成完成: %d 个", len(chart_configs))
    except Exception as exc:
        logger.error("图表配置生成失败: %s", exc)
        chart_configs = []
        result["charts"] = []

    # Step 2: 生成 Markdown 报告（始终执行）
    try:
        output_dir.mkdir(parents=True, exist_ok=True)                     # 确保输出目录存在
        md_path = output_dir / f"分析洞察报告_{asin}.md"                   # 如 "分析洞察报告_B0C123ABCD.md"
        md_content = _build_md_content(analysis_data, creator, asin)     # 构建 MD 内容
        md_path.write_text(md_content, encoding="utf-8")                  # 写入文件
        result["md_path"] = str(md_path)
        logger.info("MD 报告已生成: %s", md_path)
    except Exception as exc:
        logger.error("Markdown 报告生成失败: %s", exc)

    # Step 3: 生成 HTML 看板（template_name=None 时跳过）
    try:
        template_name = output_config.get("template_name")
        if template_name is None:                                         # 用户传了 None → 跳过
            logger.info("已跳过 HTML 看板生成（用户未选择模板）")
        else:
            if not template_name:                                          # 空字符串 → 取第一个模板
                templates = list_templates()
                template_name = templates[0]["name"] if templates else "premium-gold"

            html_path = output_dir / f"可视化洞察报告_{asin}.html"          # 如 "可视化洞察报告_B0C123ABCD.html"
            _write_html_dashboard(
                html_path, analysis_data, chart_configs, template_name, asin, creator
            )
            result["html_path"] = str(html_path)
            logger.info("HTML 看板已生成: %s", html_path)
    except Exception as exc:
        logger.error("HTML 看板生成失败: %s", exc)

    # Step 4: 可选飞书同步
    if output_config.get("sync_feishu", False):                           # 只有开启才执行
        try:
            from src.feishu_sync import sync_report                        # 运行时导入（不安装不影响）

            # 读取刚写好的 MD 报告内容
            md_content = ""
            if result["md_path"]:
                try:
                    md_content = Path(result["md_path"]).read_text(encoding="utf-8")
                except Exception:
                    md_content = analysis_data.get("insights_md", "")      # 降级：用原始数据

            product_name = analysis_data.get("product_name", asin)
            title = f"{product_name} 评论深度分析报告"
            feishu_result = sync_report(title, md_content, chart_configs)  # 调用飞书同步
            result["feishu_result"] = feishu_result
        except Exception as exc:
            logger.error("飞书同步异常（不影响主流程）: %s", exc)
            result["feishu_result"] = {
                "success": False,
                "doc_url": "",
                "whiteboard_urls": [],
                "whiteboard_count": 0,
                "error": f"飞书同步异常: {exc}",
            }

    logger.info(
        "输出生成完成: md=%s, html=%s, feishu=%s",
        bool(result["md_path"]),
        bool(result["html_path"]),
        result["feishu_result"].get("success", False),
    )
    return result


# ---------------------------------------------------------------------------
# 向后兼容 — 类封装
# ---------------------------------------------------------------------------

class OutputManager:
    """
    输出管理器类封装（向后兼容 V1 调用方式）

    老代码可能这样用：
        mgr = OutputManager()
        mgr.generate_outputs(data, output_dir, asin, template="premium-gold")

    新代码推荐直接用函数式 API：
        generate_outputs(data, output_config={"template_name": "premium-gold"})
    """

    def generate_outputs(
        self,
        analysis_data: Dict,
        output_dir: Path,
        asin: str,
        template_name: str = "premium-gold",
        feishu_sync: bool = False,
        creator: str = "AI Assistant",
    ) -> Dict:
        """
        生成所有输出文件（类方法，内部转发到函数式 API）

        Args:
            analysis_data: 分析结果数据
            output_dir: 输出目录
            asin: 产品 ASIN
            template_name: 模板名称
            feishu_sync: 是否同步飞书
            creator: 报告署名

        Returns:
            输出结果字典
        """
        return generate_outputs(
            analysis_data,
            output_config={                                                # 类参数 → 字典
                "template_name": template_name,
                "sync_feishu": feishu_sync,
                "output_dir": str(output_dir),
                "asin": asin,
                "creator": creator,
            },
        )

    def select_template_interactive(self) -> str:
        """交互式模板选择（实例方法，转发到模块函数）"""
        return select_template()
