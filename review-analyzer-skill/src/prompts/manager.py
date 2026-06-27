"""
Prompt Manager Module V2.0

V2.0 prompt 管理器：把 prompt 从 Python 字符串代码中抽离成独立的 .md 文件，
14 个章节各自一个文件，按需组装。支持条件章节（如"有时间数据才出现时间趋势章"）。

vs V1 (templates.py) 的区别：
- V1: prompt 直接写在 Python 字符串里，改一个字要改代码
- V2: prompt 写在独立的 .md 文件中，用文本编辑器就能改，不改代码
- V2: 支持数据预处理（噪声过滤、信度标注、长尾聚合）
- V2: 支持条件章节（根据数据有无动态开关）
"""

import ast                                                               # 安全解析 Python 字面量（tags 字符串 → dict）
import json                                                              # JSON 序列化（评论数据转 JSON 传给 AI）
import logging                                                           # 日志
import re                                                                # 正则：检查未替换的占位符
from datetime import datetime                                            # 时间戳
from pathlib import Path                                                 # 文件路径处理
from typing import Any, Dict, List, Optional, Tuple                      # 类型注解

logger = logging.getLogger(__name__)

# ==================== 路径常量 ====================

# prompt 文件存放目录：此文件所在目录 = src/prompts/
PROMPTS_DIR = Path(__file__).parent
# 章节文件存放目录：src/prompts/chapters/
CHAPTERS_DIR = PROMPTS_DIR / "chapters"

# 三类顶层 prompt 模板文件映射（不包含章节，章节单独管理）
# 名字 → 文件路径
PROMPT_FILES: Dict[str, Path] = {
    "tagging": PROMPTS_DIR / "tagging.md",                               # 打标 prompt（Phase 1 用）
    "persona": PROMPTS_DIR / "persona.md",                               # 画像 prompt（Phase 2 用）
    "insights_v2": PROMPTS_DIR / "insights_v2.md",                       # 洞察报告框架 prompt（Phase 3 用）
}

# 章节配置：14 个章节的编号 → 元数据
# 每个章节对应 chapters/ 目录下的一个 .md 文件
# conditional=True 的章节会根据上下文动态决定是否包含
CHAPTER_CONFIG: Dict[int, Dict[str, Any]] = {
    1: {"file": "chapter_01_overview.md", "conditional": False, "key": "overview"},
    2: {"file": "chapter_02_stats.md", "conditional": False, "key": "stats"},
    3: {"file": "chapter_03_persona.md", "conditional": False, "key": "persona"},
    4: {"file": "chapter_04_value.md", "conditional": False, "key": "value"},
    5: {"file": "chapter_05_painpoints.md", "conditional": False, "key": "painpoints"},
    6: {"file": "chapter_06_recommendations.md", "conditional": False, "key": "recommendations"},
    7: {"file": "chapter_07_opportunities.md", "conditional": False, "key": "opportunities"},
    8: {"file": "chapter_08_user_stories.md", "conditional": False, "key": "user_stories"},
    9: {
        "file": "chapter_09_time_trend.md",
        "conditional": True,                                               # 条件章节！
        "condition_field": "has_review_date",                              # 只有当 context["has_review_date"]=True 才启用
        "key": "time_trend",
    },
    10: {"file": "chapter_10_sentiment_gap.md", "conditional": False, "key": "sentiment_gap"},
    11: {"file": "chapter_11_keyword_clustering.md", "conditional": False, "key": "keyword_clustering"},
    12: {"file": "chapter_12_purchase_funnel.md", "conditional": False, "key": "purchase_funnel"},
    13: {"file": "chapter_13_action_dashboard.md", "conditional": False, "key": "action_dashboard"},
    14: {"file": "chapter_appendix_data.md", "conditional": False, "key": "data_appendix"},
}


class PromptLoadError(Exception):
    """Prompt 加载异常（文件不存在、读取失败等）"""
    pass


# ==================== 核心加载函数 ====================


def load_prompt(name: str) -> str:
    """
    加载指定的顶层 prompt 模板文件（tagging / persona / insights_v2）

    Args:
        name: 模板名称，必须是 PROMPT_FILES 中的 key

    Returns:
        str: 模板文件的完整内容

    Raises:
        ValueError: 未知的模板名称
        PromptLoadError: 文件不存在或读取失败
    """
    if name not in PROMPT_FILES:                                         # 名字不在注册表中
        available = ", ".join(PROMPT_FILES.keys())
        raise ValueError(f"未知的模板名称 '{name}'，可用模板: {available}")

    file_path = PROMPT_FILES[name]                                       # 拿到文件路径

    if not file_path.exists():                                            # 文件不存在
        raise PromptLoadError(f"模板文件不存在: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")                   # 读取文件全部内容
        logger.debug("成功加载模板: %s (%d 字符)", name, len(content))
        return content
    except OSError as e:                                                  # 读取失败
        raise PromptLoadError(f"读取模板文件失败 [{file_path}]: {e}") from e


def load_chapter(chapter_num: int) -> str:
    """
    加载指定章节的 prompt 模板文件

    Args:
        chapter_num: 章节编号 (1-14)

    Returns:
        str: 章节 prompt 内容

    Raises:
        ValueError: 章节编号不在 1-14 范围内
        PromptLoadError: 章节文件不存在或读取失败
    """
    if chapter_num not in CHAPTER_CONFIG:                                # 无效编号
        raise ValueError(f"章节编号必须在 1-14 之间，当前: {chapter_num}")

    config = CHAPTER_CONFIG[chapter_num]                                  # 拿该章的配置
    file_path = CHAPTERS_DIR / config["file"]                             # 拼接完整路径

    if not file_path.exists():
        raise PromptLoadError(f"章节文件不存在: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        logger.debug("成功加载章节 %d: %s (%d 字符)", chapter_num, config["file"], len(content))
        return content
    except OSError as e:
        raise PromptLoadError(f"读取章节文件失败 [{file_path}]: {e}") from e


def list_chapters() -> List[Dict[str, Any]]:
    """
    列出所有可用的章节配置（供外部查询有哪些章节）

    Returns:
        章节配置列表，每项含 chapter_num, key, file, conditional 等
    """
    result: List[Dict[str, Any]] = []
    for num, config in CHAPTER_CONFIG.items():
        result.append({
            "chapter_num": num,                                            # 章节编号
            "key": config["key"],                                          # 章节标识符（如 "overview"）
            "file": config["file"],                                        # 对应文件名
            "conditional": config["conditional"],                          # 是否是条件章节
            "condition_field": config.get("condition_field"),               # 条件字段名（条件章节才有）
        })
    return result


def get_active_chapters(context: Optional[Dict[str, Any]] = None) -> List[int]:
    """
    获取当前条件下启用（活跃）的章节编号列表

    调用 _resolve_conditionals 做实际的条件判断过滤

    Args:
        context: 条件上下文（如 {"has_review_date": True}）

    Returns:
        活跃章节编号列表
    """
    return _resolve_conditionals(None, context)                           # chapters=None → 不指定则包含所有


def get_chapter_info(chapter_num: int) -> Optional[Dict[str, Any]]:
    """
    获取指定章节的配置信息（查询单章元数据）

    Returns:
        章节配置字典，不存在返回 None
    """
    config = CHAPTER_CONFIG.get(chapter_num)
    if config is None:
        return None
    return {
        "chapter_num": chapter_num,
        "key": config["key"],
        "file": config["file"],
        "conditional": config["conditional"],
        "condition_field": config.get("condition_field"),
    }


# ==================== 内部工具函数 ====================


def _resolve_conditionals(
    chapters: Optional[List[int]],
    context: Optional[Dict[str, Any]],
) -> List[int]:
    """
    根据条件上下文解析最终需要包含的章节列表

    逻辑：
    1. 如果 chapters 指定了 → 用指定的
    2. 如果 chapters 为 None → 包含所有章节
    3. 对 conditional=True 的章节 → 检查 context 中对应条件字段
       → 条件满足才保留，不满足就跳过

    例子：
    - 评论没有日期数据 → context["has_review_date"]=False → 跳过第9章（时间趋势）
    - 评论有日期数据 → context["has_review_date"]=True → 保留第9章

    Args:
        chapters: 指定的章节列表（None=全部）
        context: 条件上下文字典

    Returns:
        解析后的章节编号列表
    """
    if chapters is not None:                                              # 用户指定了章节列表
        target_chapters = chapters
    else:                                                                 # 没指定 → 全部章节
        target_chapters = list(CHAPTER_CONFIG.keys())

    resolved: List[int] = []                                              # 最终结果
    context = context or {}                                                # 防止 None

    for num in target_chapters:                                           # 遍历每个目标章节
        if num not in CHAPTER_CONFIG:                                     # 非法编号
            logger.warning("跳过无效章节编号: %d", num)
            continue

        config = CHAPTER_CONFIG[num]                                      # 该章的配置

        # ── 检查条件章节 ──
        if config["conditional"]:                                          # 标记为条件章节
            condition_field = config.get("condition_field", "")            # 取条件字段名
            if not context.get(condition_field, False):                    # 条件不满足 → 跳过该章
                logger.info(
                    "跳过条件章节 %d（%s）：条件 '%s' 未满足",
                    num, config["key"], condition_field,
                )
                continue

        resolved.append(num)                                               # 该章通过，加入列表

    return resolved


def _render_template(template: str, variables: Dict[str, str]) -> str:
    """
    渲染模板，替换 {{PLACEHOLDER}} 格式的占位符

    用的是最简单的字符串替换，不是 Jinja2。
    占位符格式：{{变量名}}（全大写，如 {{TOTAL}}、{{ASIN}}）

    Args:
        template: 模板字符串（含 {{XXX}} 占位符）
        variables: 变量字典，key 为大写变量名

    Returns:
        渲染后的字符串
    """
    result = template

    for key, value in variables.items():
        placeholder = "{{" + key.upper() + "}}"                           # 构建占位符如 {{TOTAL}}
        result = result.replace(placeholder, str(value))                    # 替换为实际值

    # 检查是否还有未替换的占位符（防止变量漏传）
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", result)
    if remaining:
        logger.warning("存在未替换的占位符: %s", remaining)                # 提醒开发者有遗漏

    return result


def _normalize_tags(tags: Any) -> dict:
    """
    将 tags 字段统一转换为 dict

    背景：tags 在 CSV 存储时可能从 dict 变成字符串 "{'key': 'val'}"，
    需要用 ast.literal_eval 安全地转回 dict。
    """
    if isinstance(tags, dict):                                             # 已经是 dict
        return tags
    if isinstance(tags, str):                                              # 是字符串 → 尝试解析
        try:
            return ast.literal_eval(tags)                                   # 安全解析（不执行代码）
        except (ValueError, SyntaxError):
            return {}
    return {}


# ==================== 数据预处理函数 ====================
# 这些函数在 prompt 组装前对数据做清洗，
# 目的是提高 AI 输出质量（减少噪声干扰、让 AI 聚焦有效数据）

# 噪声值集合：这些值代表"数据缺失"或"无法识别"
_NOISE_VALUES = {"不明", "未提及", "无", "未知", "不明确", "其他"}


def _preprocess_dimensional_stats(
    dimensional_stats: Dict[str, Dict[str, int]],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    预处理维度统计：分离有效维度和噪声维度

    核心思路：不要让 AI 看到 67% "不明" 的数据后仍然强行做分析！
    改为标注信度，让 AI 知道哪些维度可信、哪些维度只能看附录。

    处理流程：
    1. 计算每个维度的噪声占比（"不明"/"未提及"/"无" 等）
    2. 噪声 > 60% → 标记为"[低信度]"，只放附录
    3. 噪声 ≤ 60% → 标记为"[有效]"，放入主分析 summary
    4. 有效值过多（>10个） → 做 Top 10 聚合，其余合并为"(其他聚合)"

    Args:
        dimensional_stats: 原始维度统计 {"人群_性别": {"不明": 46, "女性": 3, "男性": 1}, ...}

    Returns:
        Tuple:
            - summary: 有效维度的摘要（过滤噪声 + 聚合长尾），给 AI 主分析用
            - appendix: 完整原始数据 + 信度标注，放在报告附录用
    """
    summary_parts: Dict[str, str] = {}                                    # 主分析用的摘要
    appendix_parts: Dict[str, str] = {}                                    # 附录用的完整数据

    for dim, count_dict in dimensional_stats.items():                     # 遍历每个维度
        if not count_dict:
            continue

        total_dim = sum(count_dict.values())                              # 该维度的总人数
        if total_dim == 0:
            continue

        # 计算噪声占比
        noise_count = sum(
            count for val, count in count_dict.items() if val in _NOISE_VALUES
        )
        noise_ratio = noise_count / total_dim                              # 噪声比例（0.0-1.0）
        noise_pct = noise_ratio * 100                                       # 噪声百分比

        # 过滤掉噪声值，只保留有效值
        valid_items = {
            val: count
            for val, count in count_dict.items()
            if val not in _NOISE_VALUES and count > 0
        }

        # 有效值过多 → Top 10 聚合 + 长尾折叠
        if len(valid_items) > 10:
            sorted_items = sorted(valid_items.items(), key=lambda x: x[1], reverse=True)
            top_items = dict(sorted_items[:10])                             # 前10
            other_count = sum(v for _, v in sorted_items[10:])              # 其余合并
            if other_count > 0:
                top_items["(其他聚合)"] = other_count
            valid_items = top_items

        # ── 构建 appendix（完整原始数据 + 信度标注） ──
        if noise_ratio > 0.6:
            reliability_label = f"[低信度: {noise_pct:.0f}% 数据缺失]"     # 噪声太高，标记为不可信
        else:
            reliability_label = "[有效]"                                    # 数据较完整，可信

        appendix_table = f"**{dim}** {reliability_label}\n\n"
        appendix_table += f"| {dim} 类别 | 人数 | 占比 |\n| :--- | :--- | :--- |\n"
        for val, count in count_dict.items():                               # 附录包含所有数据（含噪声）
            appendix_table += f"| {val} | {count} | {count / total_dim * 100:.1f}% |\n"
        appendix_parts[dim] = appendix_table

        # ── 构建 summary（只有有效维度，且不含噪声行） ──
        if noise_ratio <= 0.6 and valid_items:                               # 可信 + 有有效值
            valid_total = max(sum(valid_items.values()), 1)
            summary_table = f"**{dim}**\n\n"
            summary_table += f"| {dim} 类别 | 人数 | 占比 |\n| :--- | :--- | :--- |\n"
            for val, count in valid_items.items():
                summary_table += (
                    f"| {val} | {count} | {count / valid_total * 100:.1f}% |\n"
                )
            summary_parts[dim] = summary_table
        elif noise_ratio > 0.6:                                              # 低信度维度
            # summary 中只放一行提示，让 AI 别瞎分析
            summary_parts[dim] = (
                f"**{dim}**: 数据缺失率 {noise_pct:.0f}%，详见附录。"
            )

    return summary_parts, appendix_parts


def _build_core_stats(stats: Dict[str, Any]) -> str:
    """
    构建核心统计数据文本（每章都需要参考的关键数据面包屑）

    从 stats 中提取最关键的指标，以简洁的 bullet points 格式呈现。
    包括：情感分布、Top 15 高频标签、复购意愿、竞品提及。

    Returns:
        核心统计的 Markdown bullet points 文本
    """
    lines: List[str] = []
    total_count = max(stats.get("total", 1), 1)                            # 避免除零

    # ── 情感分布 ──
    sentiment_data = stats.get("sentiment", {})
    if sentiment_data:
        lines.append("**情感分布**:")
        for s, c in sentiment_data.items():
            lines.append(f"  - {s}: {c} 条 ({c / total_count * 100:.1f}%)")

    # ── 高频标签 Top 15 ──
    top_tags_data = stats.get("top_tags", {})
    if top_tags_data:
        lines.append("")
        lines.append("**高频标签 (Top 15)**:")
        for i, (t, c) in enumerate(list(top_tags_data.items())[:15]):
            lines.append(f"  {i + 1}. {t}: {c} 次")

    # ── 从 dimensional_stats 提取复购意愿 ──
    dimensional_stats = stats.get("dimensional_stats", {})

    repurchase_dims = [d for d in dimensional_stats                           # 找到含"复购/回购/再购"的维度
                       if "复购" in d or "回购" in d or "再购" in d]
    for dim_key in repurchase_dims:
        dim_data = dimensional_stats[dim_key]
        total_dim = max(sum(dim_data.values()), 1)
        positive_count = sum(
            c for v, c in dim_data.items()
            if v not in _NOISE_VALUES and c > 0
        )
        lines.append("")
        lines.append(f"**{dim_key}**: 有意愿 {positive_count}/{total_dim} ({positive_count / total_dim * 100:.1f}%)")

    # ── 从 dimensional_stats 提取竞品信息 ──
    competitor_dims = [d for d in dimensional_stats
                       if "竞品" in d or "品牌" in d or "对比" in d]
    for dim_key in competitor_dims:
        dim_data = dimensional_stats[dim_key]
        total_dim = max(sum(dim_data.values()), 1)
        valid_items = {v: c for v, c in dim_data.items() if v not in _NOISE_VALUES and c > 0}
        if valid_items:
            top_competitors = sorted(valid_items.items(), key=lambda x: x[1], reverse=True)[:5]
            competitor_str = ", ".join(f"{v}({c})" for v, c in top_competitors)
            lines.append("")
            lines.append(f"**{dim_key}**: {competitor_str}")

    return "\n".join(lines) if lines else "无核心统计数据"


def _render_personas_details(personas: List[Dict[str, Any]]) -> str:
    """
    格式化用户画像详情，过滤掉无意义的噪声标签值

    只展示有意义的标签（去掉"不明""未提及""无"等无效值），
    避免在 prompt 中充斥大量无意义信息浪费 token 且干扰 AI 判断。
    """
    personas_details: List[str] = []
    for i, p in enumerate(personas):
        tags = _normalize_tags(p.get("tags", {}))
        # 过滤噪声标签（"不明""未提及"等没意义的值）
        meaningful_tags = {
            k: v for k, v in tags.items()
            if v and v not in _NOISE_VALUES
        }
        detail = f"### 画像 {i + 1}: {p['name']} ({p['count']} 条)\n"
        if meaningful_tags:
            detail += "标签特征: " + ", ".join(
                f"{k}:{v}" for k, v in meaningful_tags.items()
            )
        else:
            detail += "标签特征: 无有效标签"
        personas_details.append(detail)
    return "\n\n".join(personas_details) if personas_details else "无画像数据"


# ==================== 业务构建函数 ====================
# 以下三个函数是外部调用的入口


def build_tagging_prompt(reviews: List[Dict[str, Any]]) -> str:
    """
    构建批量评论打标 prompt（V2 版本）

    用 manager 的模板加载+渲染机制替代 V1 的 Python 字符串模板。
    不过当前 Phase 1 实际用的是 V1 的 get_tagging_prompt_batch()，
    这个 V2 版本保留以备后续切换。

    Args:
        reviews: 评论列表

    Returns:
        构建完成的 prompt 字符串
    """
    if not reviews:
        raise ValueError("评论列表不能为空")

    template = load_prompt("tagging")                                      # 加载 tagging.md 模板

    # 精简评论数据，只保留 AI 需要的字段
    simplified_reviews: List[Dict[str, Any]] = []
    for r in reviews:
        if not r.get("review_id"):                                         # 必须有 review_id
            logger.warning("跳过缺少 review_id 的评论: %s", r.get("title", "unknown"))
            continue
        simplified_reviews.append({
            "review_id": r.get("review_id", ""),
            "title": r.get("title", ""),
            "body": r.get("body", ""),
            "rating": r.get("rating", ""),
        })

    if not simplified_reviews:
        raise ValueError("没有有效的评论数据（所有评论缺少 review_id）")

    reviews_json = json.dumps(simplified_reviews, ensure_ascii=False, indent=2)  # 转 JSON 数组

    variables: Dict[str, str] = {
        "BATCH_SIZE": str(len(simplified_reviews)),                        # 批次数
        "REVIEWS_DATA": reviews_json,                                       # 评论 JSON 数组
    }

    prompt = _render_template(template, variables)                          # 替换占位符
    logger.info("构建打标 prompt 完成: %d 条评论, %d 字符", len(simplified_reviews), len(prompt))
    return prompt


def build_persona_prompt(
    tagged_data: List[Dict[str, Any]],
    total_reviews: int,
    tagged_reviews: int,
) -> str:
    """
    构建用户画像分析 prompt（V2 版本，当前未实际使用）

    同 build_tagging_prompt，保留给后续切换 V2。
    """
    template = load_prompt("persona")

    tagged_json = json.dumps(tagged_data, ensure_ascii=False, indent=2)

    variables: Dict[str, str] = {
        "TOTAL_REVIEWS": str(total_reviews),
        "TAGGED_REVIEWS": str(tagged_reviews),
        "TAGGED_DATA": tagged_json,
    }

    prompt = _render_template(template, variables)
    logger.info("构建画像 prompt 完成: %d 条数据, %d 字符", len(tagged_data), len(prompt))
    return prompt


def build_insights_prompt(
    stats: Dict[str, Any],
    personas: List[Dict[str, Any]],
    samples: List[Dict[str, Any]],
    asin: str,
    product_name: Optional[str] = None,
    chapters: Optional[List[int]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    构建洞察报告 V2 prompt（Phase 3 实际使用的入口）

    V2 的核心改进：
    1. 数据预处理：分离有效维度/噪声维度 → AI 不会被 67% "不明" 误导
    2. 条件章节：有没有时间数据 → 自动决定是否包含第9章
    3. 分层注入：核心统计(bullets) + 有效维度(summary) + 附录(appendix)
    4. 14 章独立文件：每章 prompt 在 chapters/ 目录下独立维护

    组装流程：
    load_prompt("insights_v2")  →  加载顶层框架
    _resolve_conditionals()     →  决定哪些章节要
    load_chapter(N)             →  逐章加载 prompt
    _preprocess_dimensional_stats() → 分离有效/噪声维度
    _build_core_stats()         →  构建核心统计 bullet points
    _render_personas_details()  →  格式化画像（过滤噪声标签）
    _render_template()          →  替换所有 {{VAR}} 占位符
    → 最终返回完整 prompt

    Args:
        stats: 统计数据
        personas: 画像列表
        samples: 黄金样本列表
        asin: 产品码
        product_name: 产品名（可选）
        chapters: 指定章节列表（None=全部适用章节）
        context: 条件上下文：
            - has_review_date: 是否有评论日期数据 → 控制第9章
            - time_distribution_text: 时间分布数据文本

    Returns:
        构建完成的完整 prompt 字符串（直接传 CLI）
    """
    template = load_prompt("insights_v2")                                  # 加载顶层框架模板

    # ── Step 1: 解析条件章节 ──
    context = context or {}
    resolved_chapters = _resolve_conditionals(chapters, context)           # 条件过滤，返回最终启用的章节编号列表，例如 [1,2,3,4,5,6,7,8,10,11,12,13,14]

    # ── Step 2: 加载章节 prompt 并拼接 ──
    chapter_prompts: List[str] = []
    for num in resolved_chapters:
        try:
            chapter_content = load_chapter(num)                              # 从文件加载每个章节
            chapter_prompts.append(chapter_content)
        except PromptLoadError as e:
            logger.error("加载章节 %d 失败，跳过: %s", num, e)
    chapter_prompts_text = "\n\n---\n\n".join(chapter_prompts)              # 用 --- 分隔各章

    # ── Step 3: 数据预处理 — 分离有效维度 vs 噪声维度 ──
    dimensional_stats_raw = stats.get("dimensional_stats", {})
    dim_summary_parts, dim_appendix_parts = _preprocess_dimensional_stats(
        dimensional_stats_raw
    )

    # 构建维度摘要（主分析用，只含有效维度）
    if dim_summary_parts:
        dimensional_summary_text = "\n\n".join(dim_summary_parts.values())
    else:
        dimensional_summary_text = "无有效维度分布数据"

    # 构建维度附录（完整数据 + 信度标注）
    if dim_appendix_parts:
        dimensional_appendix_text = "# 维度统计附录\n\n"
        dimensional_appendix_text += "以下为所有维度的完整统计数据，每项标注了信度等级。\n\n"
        dimensional_appendix_text += "\n\n".join(dim_appendix_parts.values())
    else:
        dimensional_appendix_text = "无维度统计数据"

    # ── Step 4: 构建核心统计 bullet points ──
    core_stats_text = _build_core_stats(stats)

    # ── Step 5: 格式化用户画像（过滤噪声） ──
    personas_details_text = _render_personas_details(personas)

    # ── Step 6: 格式化黄金样本 ──
    samples_details: List[str] = []
    for i, s in enumerate(samples):
        tags = _normalize_tags(s.get("tags", {}))
        sample = f"### 样本 {i + 1}\n"
        sample += f"**情感**: {s.get('sentiment', '不明')}\n"
        sample += f"**内容**: {s.get('body', '')[:300]}...\n"               # 截断到300字
        sample += f"**标签**: {', '.join(f'{k}:{v}' for k, v in tags.items() if v)}"
        samples_details.append(sample)
    golden_samples = "\n\n".join(samples_details) if samples_details else "无样本数据"

    # ── Step 7: 时间分布数据 ──
    time_distribution = context.get("time_distribution_text", "无时间分布数据")

    # ── Step 8: 分层组装所有变量 → 填入模板 ──
    variables: Dict[str, str] = {
        "TOTAL": str(stats.get("total", 0)),                                # 总评论数
        "TAGGED": str(stats.get("tagged", 0)),                              # 成功打标数
        "ASIN": asin,                                                       # 产品码
        "PRODUCT_NAME": product_name or asin,                                # 产品名（默认用 ASIN）
        "PERSONAS_COUNT": str(len(personas)),                                # 画像个数
        "PERSONAS_DETAILS": personas_details_text,                           # 画像详情
        "CORE_STATS": core_stats_text,                                       # 核心统计
        "DIMENSIONAL_SUMMARY": dimensional_summary_text,                     # 维度摘要（有效数据）
        "DIMENSIONAL_APPENDIX": dimensional_appendix_text,                   # 维度附录（完整+信度）
        "SAMPLES_COUNT": str(len(samples)),                                  # 样本数
        "GOLDEN_SAMPLES": golden_samples,                                    # 黄金样本
        "TIME_DISTRIBUTION": time_distribution,                               # 时间分布
        "CHAPTER_PROMPTS": chapter_prompts_text,                             # 所有章节 prompt 拼接
    }

    prompt = _render_template(template, variables)                          # 替换所有 {{XXX}} 占位符

    active_chapters = [str(n) for n in resolved_chapters]
    logger.info(
        "构建洞察 V2 prompt 完成: 章节 [%s], %d 字符",
        ", ".join(active_chapters), len(prompt),
    )
    return prompt
