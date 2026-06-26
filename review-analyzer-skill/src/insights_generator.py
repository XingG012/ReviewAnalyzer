"""
洞察报告生成模块 V1.0 - CLI 原生版

Phase 3 的核心：统计打标数据 → 组装 prompt → 调 CLI 生成 14 章 Markdown 报告。

流程：
1. calculate_stats_summary()  → 从打标数据中统计情感分布、标签频率、维度分布
2. generate_insights()        → 组装 V2 prompt → subprocess 调 CLI → 解析 strategic_json
3. _ensure_mermaid_charts()   → 兜底：AI 没画 mermaid 图就自动生成

统一使用 subprocess 调用宿主 CLI 引擎生成洞察报告。
支持 claude / opencode 双引擎，由 config 自动适配。
"""

import json                                                             # JSON 解析：提取 strategic_json
import logging                                                          # 日志记录
import re                                                               # 正则：匹配章节标题、提取 strategic_json
import subprocess                                                       # 子进程：调用 CLI 生成报告
from typing import List, Dict, Optional                                 # 类型注解
from collections import Counter                                         # 计数器：统计标签频率
from datetime import datetime                                           # 生成时间戳

# 模块级缓存：最近一次 generate_insights() 提取的 strategic_json
# 供 HTML 看板使用（护城河、软肋、执行矩阵等结构化数据）
_last_strategic_data: Dict = {}

from src.config import config                                           # 全局配置
from src.prompts.templates import get_insights_prompt_md, get_insights_prompt_txt  # V1 prompt 模板

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 核心函数 ====================

def calculate_stats_summary(tagged_reviews: List[Dict]) -> Dict:
    """
    计算统计摘要（Phase 3 第一步，纯 Python 计算，不调 AI）

    从 Phase 1 输出的打标评论中提取：
    1. 情感分布（强烈推荐几条、中立几条...）
    2. 高频标签 Top 30（如 "质量_材质:优秀" 出现了 45 次）
    3. 全维度分布（每个维度下面各类别的占比）
    4. 平均评分

    为什么保留"不明/未提及"数据？
    → 不在此处过滤，让 AI 看到真实的缺失率数据
    → AI 会根据 Prompt 中的"长尾折叠"和"反幻觉"原则自主处理

    Args:
        tagged_reviews: Phase 1 输出的打标评论列表

    Returns:
        统计摘要字典:
        {
            "total": 100,                    # 总评论数
            "tagged": 95,                    # 成功打标数
            "sentiment": {                   # 情感分布
                "强烈推荐": 30, "推荐": 40, "中立": 15, "不推荐": 8, "强烈不推荐": 2
            },
            "top_tags": {                    # 高频标签 Top 30
                "人群_性别:男性": 45, "质量_材质:优秀": 38, ...
            },
            "dimensional_stats": {           # 按维度分组的统计
                "人群_性别": {"男性": 45, "女性": 30, "不明": 20},
                "质量_材质": {"优秀": 38, "一般": 25, "未提及": 32},
                ...
            },
            "avg_rating": 4.2                # 平均评分
        }
    """
    # 空数据保护
    if not tagged_reviews:
        return {"total": 0, "tagged": 0, "sentiment": {}, "top_tags": {}}

    total = len(tagged_reviews)
    tagged_count = sum(1 for r in tagged_reviews if r.get("tags"))     # 有标签的算成功打标

    # 1. 统计情感分布
    sentiment_counter = Counter()                                        # {"强烈推荐": 30, "推荐": 40, ...}
    for review in tagged_reviews:
        sentiment = review.get("sentiment", "中立")                      # 默认"中立"
        if sentiment:
            sentiment_counter[sentiment] += 1

    sentiment_dist = dict(sentiment_counter)                              # Counter → 普通 dict

    # 2. 统计高频标签和全维度分布
    # 扁平化格式: "维度_标签名:值" 如 "人群_性别:男性"
    tag_counter = Counter()                                              # 扁平标签计数
    dimensional_stats = {}                                                # 按维度分组的计数

    # 关键设计：不过滤"不明"或"未提及"
    # 让大模型看到真实的数据分布（特别是缺失率），自主决定如何处理
    for review in tagged_reviews:
        tags = review.get("tags", {})
        for tag_key, tag_value in tags.items():                          # 遍历22维标签
            if tag_value:                                                 # 跳过空值
                # 扁平化的高频标签
                combined_key = f"{tag_key}:{tag_value}"                   # 如 "人群_性别:男性"
                tag_counter[combined_key] += 1

                # 结构化的维度统计
                if tag_key not in dimensional_stats:                      # 第一次遇到该维度
                    dimensional_stats[tag_key] = Counter()
                dimensional_stats[tag_key][tag_value] += 1                # 该维度下的这个值 +1

    # 取 Top 30 标签（给 AI 看的重点标签）
    top_tags = dict(tag_counter.most_common(30))

    # 将 Counter 转为普通 dict（每个维度取 Top 50 防止数据过大）
    for dim in dimensional_stats:
        dimensional_stats[dim] = dict(dimensional_stats[dim].most_common(50))

    # 3. 计算平均评分
    ratings = [r.get("rating", 0) for r in tagged_reviews if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "total": total,
        "tagged": tagged_count,
        "sentiment": sentiment_dist,
        "top_tags": top_tags,
        "dimensional_stats": dimensional_stats,
        "avg_rating": avg_rating
    }


def generate_insights(
    stats: Dict,
    personas: List[Dict],
    golden_samples: List[Dict],
    asin: str,
    product_name: str = None
) -> str:
    """
    生成洞察报告（Phase 3 的核心分发器）

    流程：
    1. 用 V2 Prompt 管理器组装 prompt（含数据预处理、噪声过滤、分层注入）
    2. 失败则降级到 V1 prompt 模板
    3. 通过 subprocess CLI 生成报告
    4. 兜底：检查并补全 mermaid 图表
    5. 剥离 <strategic_json> 块（存到全局变量供 HTML 看板使用）

    Args:
        stats: calculate_stats_summary() 返回的统计字典
        personas: Phase 2 识别出的用户画像列表
        golden_samples: Phase 2 选的黄金样本列表
        asin: 产品 ASIN
        product_name: 产品名称（可选）

    Returns:
        str: Markdown 格式的洞察报告。失败返回空字符串。
    """
    # ── Step 1: 组装 prompt（V2 优先，V1 降级兜底） ──
    try:
        from src.prompts.manager import build_insights_prompt as _build_v2_prompt

        # 构建附加上下文（检查是否有日期数据 → 决定是否启用时间趋势章节）
        context = {}
        has_date = any(
            r.get("date") and r.get("date") not in ("", "nan", "None")
            for r in golden_samples                                        # 检查黄金样本中是否有有效日期
        )
        if has_date:
            context["has_review_date"] = True                               # 有日期 → 启用时间趋势分析
            context["time_distribution_text"] = "用户评论包含日期信息，可进行时间趋势分析"

        prompt = _build_v2_prompt(                                          # V2: 14章结构 + 数据预处理
            stats=stats,
            personas=personas,
            samples=golden_samples,
            asin=asin,
            product_name=product_name,
            context=context,
        )
        logger.info("使用 V2.1 Prompt 管理器（14 章结构 + 数据预处理）")
    except Exception as exc:                                                # V2 加载失败 → 降级到 V1
        logger.warning("V2 Prompt 加载失败，降级到 V1: %s", exc)
        if config.INSIGHTS_FORMAT == "md":                                  # 根据配置选 MD 或 TXT 模板
            prompt = get_insights_prompt_md(
                stats=stats, personas=personas, samples=golden_samples,
                asin=asin, product_name=product_name
            )
        else:
            prompt = get_insights_prompt_txt(
                stats=stats, personas=personas, samples=golden_samples,
                asin=asin, product_name=product_name
            )

    # ── Step 2: 调 CLI 生成报告 ──
    report_text = _generate_via_cli(prompt, asin)

    # ── Step 3: Mermaid 兜底（AI 可能偷懒没画图） ──
    if report_text:
        report_text = _ensure_mermaid_charts(report_text, stats, personas)

    # ── Step 4: 剥离 <strategic_json> 块 ──
    # strategic_json 是藏在报告末尾的结构化数据（护城河/软肋/执行矩阵）
    # 需要从报告正文中剥离，存到全局变量中供 HTML 看板使用
    global _last_strategic_data
    _last_strategic_data = {}
    if report_text and "<strategic_json>" in report_text:
        import re as _re
        # 先提取 strategic_json 存入缓存（HTML 看板会通过 get_last_strategic_data() 读取）
        _match = _re.search(
            r'<strategic_json>\s*(\{.*?\})\s*</strategic_json>',
            report_text, _re.DOTALL,                                       # DOTALL: . 匹配换行符
        )
        if _match:
            try:
                _last_strategic_data = json.loads(_match.group(1))         # JSON 解析为 Python dict
            except json.JSONDecodeError:                                    # 解析失败就留空
                pass
        # 再从报告正文中删除 strategic_json 块（保持报告干净）
        report_text = _re.sub(r'<strategic_json>.*?</strategic_json>', '', report_text, flags=_re.DOTALL).strip()

    return report_text


def _generate_via_cli(prompt: str, asin: str) -> str:
    """
    使用 CLI 引擎生成洞察报告（subprocess 调用 claude/opencode）

    和 review_analyzer._call_claude_cli 不同的地方：
    - 这个更简单，不需要重试逻辑（失败直接返回空字符串）
    - 因为 Phase 3 只调一次（不像 Phase 1 要调 N 次），重试成本高、收益低

    Args:
        prompt: 组装好的完整 prompt
        asin: 产品 ASIN（仅用于日志）

    Returns:
        str: CLI stdout 输出（报告正文），失败返回 ""
    """
    cmd = config.build_cli_cmd(prompt)                                   # 构建命令列表

    result = subprocess.run(
        cmd,
        capture_output=True,                                              # 捕获 stdout/stderr
        text=True,                                                        # 字符串模式
        timeout=config.CLI_TIMEOUT,                                       # 超时控制
        check=True                                                        # 非0返回码自动抛异常
    )

    if result.returncode != 0:                                            # 双重保险
        error_msg = result.stderr or result.stdout or "未知错误"
        logger.error(f"CLI 返回非零状态码: {error_msg}")
        return ""

    report_text = result.stdout.strip()
    if not report_text:
        logger.error("CLI 返回空内容")
        return ""

    logger.info(f"成功生成洞察报告({config.CLI_ENGINE.upper()}): ASIN={asin}, 字数={len(report_text)}")
    return report_text


def generate_insights_with_metadata(
    tagged_reviews: List[Dict],
    personas: List[Dict],
    golden_samples: List[Dict],
    asin: str,
    product_name: str = None
) -> Dict:
    """
    生成洞察报告及元数据（便捷函数，统计+报告一步到位）

    适用场景：从已打标 CSV 直接生成报告的脚本（replay、tools/ 等）

    Returns:
        {
            "report": "...",           # Markdown 报告内容
            "stats": {...},            # 统计摘要
            "generated_at": "..."      # ISO 格式生成时间
        }
    """
    # Step A: 计算统计数据
    stats = calculate_stats_summary(tagged_reviews)

    # Step B: 组装 prompt + 调 CLI 生成 Markdown 报告
    report = generate_insights(
        stats=stats,
        personas=personas,
        golden_samples=golden_samples,
        asin=asin,
        product_name=product_name
    )

    return {
        "report": report,
        "stats": stats,
        "generated_at": datetime.now().isoformat()
    }


# ==================== 辅助函数 ====================

def format_sentiment_distribution(sentiment_dist: Dict[str, int], total: int) -> str:
    """
    格式化情感分布为可读字符串
    输出如：
    - **强烈推荐**: 10 条 (10.0%)
    - **推荐**: 50 条 (50.0%)
    """
    lines = []
    for sentiment, count in sentiment_dist.items():
        percentage = (count / total * 100) if total > 0 else 0            # 计算百分比
        lines.append(f"- **{sentiment}**: {count} 条 ({percentage:.1f}%)")
    return "\n".join(lines)


def format_top_tags(top_tags: Dict[str, int], limit: int = 15) -> str:
    """
    格式化高频标签为可读字符串
    输出如：1. **人群_性别:男性**: 45 次
    """
    lines = []
    for i, (tag, count) in enumerate(list(top_tags.items())[:limit]):    # 只取前 limit 个
        lines.append(f"{i+1}. **{tag}**: {count} 次")
    return "\n".join(lines)


def validate_stats(stats: Dict) -> bool:
    """
    验证统计数据的完整性（检查必需字段是否存在）
    用于防呆：确保 stats 里至少有 total、tagged、sentiment、top_tags 四个字段
    """
    required_keys = {"total", "tagged", "sentiment", "top_tags"}
    return required_keys.issubset(stats.keys())                           # 看 required_keys 是不是 stats.keys() 的子集


def get_sentiment_percentage(stats: Dict, sentiment: str) -> float:
    """
    获取特定情感的占比（0-100）
    如：get_sentiment_percentage(stats, "强烈推荐") → 30.5
    """
    total = stats.get("total", 0)
    if total == 0:
        return 0.0
    sentiment_count = stats.get("sentiment", {}).get(sentiment, 0)
    return (sentiment_count / total) * 100


def get_top_persona(personas: List[Dict]) -> Dict:
    """
    获取样本量最大的用户画像
    用于摘要显示：比如展示"核心用户群体：家用_女性（45人）"
    """
    if not personas:
        return None
    return max(personas, key=lambda p: p.get("count", 0))                 # 按 count 取最大


def summarize_stats(stats: Dict) -> str:
    """
    生成统计的一句话摘要
    输出如："共 100 条评论，强烈推荐 40%。"
    """
    total = stats.get("total", 0)
    tagged = stats.get("tagged", 0)

    parts = [f"共 {total} 条评论"]

    if total > 0:
        # 找出最多的情感类别
        sentiment_dist = stats.get("sentiment", {})
        if sentiment_dist:
            top_sentiment = max(sentiment_dist, key=sentiment_dist.get)    # 人数最多的情感
            top_pct = get_sentiment_percentage(stats, top_sentiment)
            parts.append(f"{top_sentiment} {top_pct:.0f}%")

    return "，".join(parts) + "。"


def get_last_strategic_data() -> Dict:
    """
    获取最近一次 generate_insights() 调用中提取的 strategic_json 数据。

    这个函数是 HTML 看板和 generate_insights 之间的桥梁：
    generate_insights 把 AI 报告末尾的 <strategic_json> 解析后存到
    模块级变量 _last_strategic_data，HTML 模板通过此函数读取。

    包含：
    - moat: 护城河（产品核心优势）
    - vulnerability: 软肋（产品主要短板）
    - execution_matrix: 执行矩阵（紧急/短期/长期行动项）

    Returns:
        strategic_json 字典，可能为空。
    """
    return _last_strategic_data


# ==================== Mermaid 兜底机制 ====================
# 背景：AI 生成的报告中应该包含 4 个 mermaid 流程图，
# 但 AI 有时会"偷懒"跳过 mermaid 生成（只写文字不画图）。
# 这些函数检测缺失的图，并从统计数据中自动生成替代的 mermaid 代码。

def _ensure_mermaid_charts(report_text: str, stats: Dict, personas: List[Dict]) -> str:
    """
    确保报告中包含必需的 mermaid 图表，缺失时从数据自动生成。

    检查 4 个关键章节：
    1. 痛点章节 → 痛点严重性矩阵 (flowchart)
    2. 竞品章节 → 竞品定位思维导图 (mindmap)
    3. 话题聚类章节 → 话题聚类思维导图 (mindmap)
    4. 行动仪表盘章节 → 行动优先级矩阵 (flowchart)

    判断逻辑：章节标题存在 + 该章节内没有 mermaid → 自动注入

    Args:
        report_text: AI 生成的 Markdown 报告
        stats: 统计数据
        personas: 用户画像列表

    Returns:
        补全后的报告文本
    """
    if not report_text:
        return report_text

    # 定义 4 个必需的 mermaid 图表配置
    required_charts = [
        {
            "key": "pain_points_matrix",
            # 匹配"主要痛点与负面归因"章节标题（双语）
            "heading_patterns": [
                r"#{2,3}\s*.*(?:主要痛点|痛点与负面|痛点.*归因|Pain\s*Point)",
            ],
            "mermaid_keywords": ["graph TD", "graph LR"],                # 这类图的关键词
            "generator": _generate_pain_points_matrix,                     # 用哪个函数生成
        },
        {
            "key": "competitor_mindmap",
            # 匹配"潜在机会与差异化"章节标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:潜在机会|差异化|竞品|Opportunit|Differentiat)",
            ],
            "mermaid_keywords": ["mindmap"],
            "generator": _generate_competitor_mindmap,
        },
        {
            "key": "topic_mindmap",
            # 匹配"关键词与话题聚类"章节标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:关键词|话题聚类|Topic\s*Cluster|Keyword)",
            ],
            "mermaid_keywords": ["mindmap"],
            "generator": _generate_topic_mindmap,
        },
        {
            "key": "action_matrix",
            # 匹配"行动决策仪表盘"章节标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:行动决策|行动.*仪表盘|Action\s*Dashboard|Decision)",
            ],
            "mermaid_keywords": ["graph TD", "graph LR"],
            "generator": _generate_action_matrix,
        },
    ]

    injected_count = 0
    for chart_config in required_charts:
        # 找到章节标题的位置
        heading_match = _find_heading_match(report_text, chart_config["heading_patterns"])
        if not heading_match:
            # 章节标题不存在（AI 可能没输出这章），跳过
            continue

        # 获取该章节的文本范围（从当前标题到下一个同级标题之间）
        heading_end = heading_match.end()
        next_heading_pos = _find_next_heading_pos(
            report_text, heading_match.start(), heading_match.group(0)
        )
        section_text = report_text[heading_end:next_heading_pos]          # 该章节的正文

        # 检查该章节中是否已存在 mermaid 代码块
        has_mermaid = bool(re.search(r"```mermaid", section_text))
        if has_mermaid:
            # 有 mermaid → 检查是否含预期关键词
            has_expected_content = any(
                kw in section_text for kw in chart_config["mermaid_keywords"]
            )
            if has_expected_content:
                continue                                                   # mermaid 完整，不需要兜底

        # 需要兜底：从数据中自动生成 mermaid 并注入
        mermaid_block = chart_config["generator"](stats, personas)
        if mermaid_block:
            report_text = _inject_mermaid_after_heading(
                report_text, heading_match, mermaid_block
            )
            injected_count += 1
            logger.info("Mermaid 兜底注入: %s", chart_config["key"])

    if injected_count > 0:
        logger.info("Mermaid 兜底完成: 共注入 %d 个图表", injected_count)

    return report_text


def _find_heading_match(text: str, patterns: List[str]) -> Optional[re.Match]:
    """
    在文本中查找第一个匹配的章节标题
    按 patterns 顺序依次尝试，找到就返回
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)                    # IGNORECASE: 忽略英文大小写
        if match:
            return match
    return None


def _find_next_heading_pos(text: str, current_heading_start: int, current_heading: str) -> int:
    """
    找当前章节之后的下一个同级/更高级标题位置

    用途：确定当前章节的文本范围
    [当前标题] ...内容... [下一个 ## 或 #] ← 这就是边界

    Returns:
        下一章节的起始位置，如果没有则返回文本末尾
    """
    search_start = current_heading_start + len(current_heading)           # 从当前标题之后开始搜索
    # 匹配 ## 或 ### 开头的标题行
    next_match = re.search(r"\n#{2,3}\s+", text[search_start:])
    if next_match:
        return search_start + next_match.start()
    return len(text)                                                       # 没找到下一个标题 → 到底了


def _inject_mermaid_after_heading(
    report_text: str, heading_match: re.Match, mermaid_block: str
) -> str:
    """
    在章节标题之后注入 mermaid 代码块
    标题和 mermaid 之间保留一个空行，排版好看
    """
    insert_pos = heading_match.end()
    injection = f"\n\n{mermaid_block}\n\n"
    return report_text[:insert_pos] + injection + report_text[insert_pos:]


def _generate_competitor_mindmap(stats: Dict, personas: List[Dict]) -> str:
    """
    从竞品对比数据生成竞品定位思维导图 (mermaid mindmap)

    数据来源：stats["dimensional_stats"] 中维度名含"竞品/品牌/对比"的项
    取前 5 个竞品，按提及次数排列

    输出格式：
    ```mermaid
    mindmap
      root((竞品定位地图))
        [品牌A]
          (提及12次)
        [品牌B]
          (提及8次)
    ```
    """
    dimensional_stats = stats.get("dimensional_stats", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}     # 无意义的噪声值

    # 提取竞品相关维度（维度名含"竞品""品牌""对比"的）
    competitor_dims = {
        k: v for k, v in dimensional_stats.items()
        if any(kw in k for kw in ["竞品", "品牌", "对比"])
    }

    # 收集竞品数据（品牌名 + 提及次数）
    competitors = []
    for dim_key, dim_data in competitor_dims.items():
        valid_items = {
            val: count for val, count in dim_data.items()
            if val not in noise_values and count > 0                        # 过滤噪声
        }
        # 按提及次数降序，取前 5
        sorted_items = sorted(valid_items.items(), key=lambda x: x[1], reverse=True)[:5]
        for val, count in sorted_items:
            # 避免重复添加（不同维度可能提到同一个品牌）
            if not any(c["name"] == val for c in competitors):
                competitors.append({"name": val, "count": count})

    competitors.sort(key=lambda x: x["count"], reverse=True)
    competitors = competitors[:5]                                          # 最多 5 个

    # 构建 mermaid mindmap
    lines = ["mindmap", "  root((竞品定位地图))"]

    if competitors:
        for comp in competitors:
            safe_name = _sanitize_mermaid_text(comp["name"])               # 清理特殊字符
            count_info = f"提及{comp['count']}次"
            lines.append(f"    [{safe_name}]")
            lines.append(f"      ({count_info})")
    else:
        lines.append("    [无竞品数据]")
        lines.append("      (数据不足)")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _generate_topic_mindmap(stats: Dict, personas: List[Dict]) -> str:
    """
    从标签统计数据生成话题聚类思维导图 (mermaid mindmap)

    数据来源：stats["top_tags"] 的高频标签
    按维度归类（如"人群_性别"、"质量_材质"），每维度取 Top 3 标签值

    输出格式：
    ```mermaid
    mindmap
      root((话题聚类))
        [性别]
          (男性 45次)
          (女性 30次)
        [质量]
          (优秀 38次)
    ```
    """
    top_tags = stats.get("top_tags", {})
    dimensional_stats = stats.get("dimensional_stats", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 按维度归类标签（维度名 -> Top 3 值）
    dimension_topics = {}
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:                                             # 不是 "维度:值" 格式，跳过
            continue
        dim_name, dim_value = tag_key.split(":", 1)                        # 拆成 维度名 和 值
        if dim_value in noise_values:
            continue
        if dim_name not in dimension_topics:
            dimension_topics[dim_name] = []
        dimension_topics[dim_name].append({"value": dim_value, "count": count})

    # 每个维度取 Top 3
    for dim_name in dimension_topics:
        dimension_topics[dim_name].sort(key=lambda x: x["count"], reverse=True)
        dimension_topics[dim_name] = dimension_topics[dim_name][:3]

    # 取总提及量最高的 5 个维度
    sorted_dims = sorted(
        dimension_topics.items(),
        key=lambda x: sum(item["count"] for item in x[1]),
        reverse=True,
    )[:5]

    # 构建 mermaid mindmap
    lines = ["mindmap", "  root((话题聚类))"]

    if sorted_dims:
        for dim_name, items in sorted_dims:
            # 维度名去掉前缀（如 "人群_性别" → "性别"）
            display_dim = dim_name.split("_")[-1] if "_" in dim_name else dim_name
            safe_dim = _sanitize_mermaid_text(display_dim)
            lines.append(f"    [{safe_dim}]")
            for item in items:
                safe_val = _sanitize_mermaid_text(item["value"])
                lines.append(f"      ({safe_val} {item['count']}次)")
    else:
        lines.append("    [无话题数据]")
        lines.append("      (数据不足)")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _generate_action_matrix(stats: Dict, personas: List[Dict]) -> str:
    """
    从痛点/卖点数据生成行动优先级矩阵 (mermaid flowchart)

    逻辑：
    - 提取负面相关标签 → 生成"快速见效"建议（Quick Wins）
    - 提取正面相关标签 → 生成"战略投入"建议（Strategic Investment）
    - 兜底 → 生成"低优先级"建议（监控/观望）

    输出格式：
    ```mermaid
    graph TD
        A[行动仪表盘] --> B[快速见效]
        A --> C[战略投入]
        A --> D[低优先级]
        B --> B1[改善材质 - 影响12位用户]
        C --> C1[巩固外观设计 - 38次正面提及]
        D --> D1[监控长尾反馈趋势]
    ```
    """
    dimensional_stats = stats.get("dimensional_stats", {})
    sentiment_data = stats.get("sentiment", {})
    top_tags = stats.get("top_tags", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 从标签中提取负面/痛点信息
    pain_points = []
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        # 识别可能的问题维度（标签键名含"痛点/不满/问题"等词）
        if any(kw in dim_name for kw in ["痛点", "不满", "问题", "缺点", "负面"]):
            pain_points.append({"value": dim_value, "count": count})

    pain_points.sort(key=lambda x: x["count"], reverse=True)

    # 从标签中提取正面/优势信息
    selling_points = []
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        if any(kw in dim_name for kw in ["卖点", "优势", "好评", "亮点", "正面"]):
            selling_points.append({"value": dim_value, "count": count})

    selling_points.sort(key=lambda x: x["count"], reverse=True)

    # 计算负面评价比例（用于推断严重程度）
    total = stats.get("total", 1)
    negative_count = sum(
        sentiment_data.get(s, 0) for s in ["不推荐", "强烈不推荐"]
    )
    negative_ratio = negative_count / total if total > 0 else 0

    # 构建行动建议三类
    quick_wins = []          # 高频痛点 → 快速修复
    strategic = []           # 中频痛点 + 稳固优势 → 战略投入
    low_priority = []        # 长尾 → 低优先级

    # 高频痛点 → Quick Win（容易改进且影响大）
    for pp in pain_points[:2]:
        safe_name = _sanitize_mermaid_text(pp["value"])
        quick_wins.append(f"{safe_name} - 影响{pp['count']}位用户")

    # 如果负面比例高但没具体痛点标签 → 从整体情感数据推断
    if negative_ratio > 0.2 and not quick_wins:
        pct = f"{negative_ratio * 100:.0f}%"
        quick_wins.append(f"改善负面评价 - {pct}差评率")

    # 中频痛点 → 长期战略优化
    for pp in pain_points[2:4]:
        safe_name = _sanitize_mermaid_text(pp["value"])
        strategic.append(f"改进{safe_name} - 战略优化")

    # 正面优势 → 巩固已有成果
    for sp in selling_points[:2]:
        safe_name = _sanitize_mermaid_text(sp["value"])
        strategic.append(f"巩固{safe_name} - {sp['count']}次正面提及")

    # Low Priority 兜底
    if not low_priority:
        low_priority.append("监控长尾反馈趋势")

    # 全空兜底
    if not quick_wins and not strategic:
        quick_wins.append("分析热门评论反馈进行改进")
        strategic.append("制定差异化竞争策略")

    # 构建 mermaid flowchart
    lines = [
        "graph TD",
        "    A[行动仪表盘] --> B[快速见效]",                                # 根节点分三叉
        "    A --> C[战略投入]",
        "    A --> D[低优先级]",
    ]

    for i, qw in enumerate(quick_wins[:2], 1):                            # 最多 2 个快速见效
        lines.append(f"    B --> B{i}[{qw}]")

    for i, si in enumerate(strategic[:2], 1):                              # 最多 2 个战略投入
        lines.append(f"    C --> C{i}[{si}]")

    for i, lp in enumerate(low_priority[:1], 1):                           # 最多 1 个低优先级
        lines.append(f"    D --> D{i}[{lp}]")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _generate_pain_points_matrix(stats: Dict, personas: List[Dict]) -> str:
    """
    从痛点/负面数据生成痛点严重性矩阵 (mermaid flowchart)

    按严重程度分三级：
    - 致命级（≥10% 的用户受影响）
    - 严重级（≥5%）
    - 一般级（<5%）

    输出格式：
    ```mermaid
    graph TD
        A[痛点分析] --> B[致命级]
        A --> C[严重级]
        A --> D[一般级]
        B --> B1[材质差 - 12%用户受影响]
        C --> C1[包装破损 - 7%用户受影响]
        D --> D1[持续监控用户反馈]
    ```
    """
    dimensional_stats = stats.get("dimensional_stats", {})
    sentiment_data = stats.get("sentiment", {})
    top_tags = stats.get("top_tags", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 提取负面/痛点相关标签
    pain_items = []
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        if any(kw in dim_name for kw in ["痛点", "不满", "问题", "缺点", "负面", "抱怨"]):
            pain_items.append({"value": dim_value, "count": count, "dim": dim_name})

    pain_items.sort(key=lambda x: x["count"], reverse=True)

    total = stats.get("total", 1)
    severe_count = sum(sentiment_data.get(s, 0) for s in ["不推荐", "强烈不推荐"])

    # 按严重程度（占比）分级
    critical = []       # ≥10%
    severe = []          # ≥5%
    moderate = []         # <5%

    for item in pain_items:
        pct = item["count"] / total * 100 if total > 0 else 0
        entry = {
            "value": _sanitize_mermaid_text(item["value"]),
            "pct": f"{pct:.0f}%",
        }
        if pct >= 10:
            critical.append(entry)
        elif pct >= 5:
            severe.append(entry)
        else:
            moderate.append(entry)

    # 没有显式痛点数据但有差评 → 从负面情感比例推断"高差评率"项
    if not pain_items and severe_count > 0:
        negative_pct = severe_count / total * 100
        critical.append({"value": "高差评率", "pct": f"{negative_pct:.0f}%"})

    # 构建 mermaid flowchart
    lines = [
        "graph TD",
        "    A[痛点分析] --> B[致命级]",
        "    A --> C[严重级]",
        "    A --> D[一般级]",
    ]

    for i, item in enumerate(critical[:2], 1):
        lines.append(f"    B --> B{i}[{item['value']} - {item['pct']}用户受影响]")

    for i, item in enumerate(severe[:2], 1):
        lines.append(f"    C --> C{i}[{item['value']} - {item['pct']}用户受影响]")

    for i, item in enumerate(moderate[:1], 1):
        lines.append(f"    D --> D{i}[{item['value']}]")

    # 空级别占位符
    if not critical:
        lines.append("    B --> B1[暂无致命级问题]")
    if not severe:
        lines.append("    C --> C1[暂无严重级问题]")
    if not moderate:
        lines.append("    D --> D1[持续监控用户反馈]")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _sanitize_mermaid_text(text: str) -> str:
    """
    清理文本使其适用于 mermaid 节点标签

    mermaid 对特殊字符敏感（括号 `[](){}`、引号 `"'` 等会破坏语法）。
    此函数保留中英文内容，移除特殊字符，截断过长文本（>40字）。

    Args:
        text: 原始文本

    Returns:
        安全文本（≤40字符，无特殊符号）
    """
    if not text:
        return "N/A"

    cleaned = text.strip()
    # 移除 mermaid 语法保留字符
    for char in ['[', ']', '(', ')', '{', '}', '"', "'", '#', '&', '|', '%']:
        cleaned = cleaned.replace(char, '')

    # 压缩连续空格
    while '  ' in cleaned:
        cleaned = cleaned.replace('  ', ' ')

    cleaned = cleaned.strip()
    if not cleaned:
        return "N/A"

    # 截断到 40 字符（避免 mermaid 节点过长溢出）
    if len(cleaned) > 40:
        cleaned = cleaned[:37] + "..."

    return cleaned
