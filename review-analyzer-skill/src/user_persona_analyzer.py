"""
用户画像分析模块（Phase 2）

基于 Phase 1 打标后的评论数据，用"场景+性别"的交叉组合来识别用户群体，
并为每个群体筛选高质量的正面+负面代表样本（黄金样本），供后续报告引用。

核心思路：
- 不使用复杂的机器学习聚类
- 直接用标签的交叉组合（如 "家用 + 女性"）作为画像名称
- 动态阈值适应不同数据量（100条以下门槛降到2）
- 维度退化兜底（场景+性别 → 仅场景 → 仅性别 → 全量用户）
"""

from typing import List, Dict, Tuple                                    # 类型注解
from collections import Counter                                         # 计数器：统计每个画像的人数
from src.config import config                                           # 全局配置（MAX_PERSONAS, PERSONA_MIN_COUNT 等）


# 预定义颜色方案（给每个画像分配一个颜色，HTML 看板展示用）
PERSONA_COLORS = [
    "#d29922",  # 金色
    "#2d9cdb",  # 蓝色
    "#27ae60",  # 绿色
    "#e74c3c",  # 红色
]

# 情感标签 → 前端 CSS 样式类（HTML 看板中控制文字颜色）
SENTIMENT_CLASS_MAP = {
    "强烈推荐": "strong-positive",                                     # 深绿色
    "推荐": "positive",                                                 # 浅绿色
    "中立": "neutral",                                                  # 灰色
    "不推荐": "negative",                                                # 橙色
    "强烈不推荐": "strong-negative",                                    # 红色
}

# 正面情感列表（用于筛选正面样本）
POSITIVE_SENTIMENTS = ["强烈推荐", "推荐"]

# 负面情感列表（用于筛选反面教材）
NEGATIVE_SENTIMENTS = ["不推荐", "强烈不推荐"]


def analyze_user_personas(tagged_reviews: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    分析用户画像并筛选代表性样本（Phase 2 的唯一对外入口）

    分两步：
    Step 1: _identify_personas() → 识别有哪些用户群体
    Step 2: _select_golden_samples() → 每个群体各选 3 正 + 3 负样本

    Args:
        tagged_reviews: Phase 1 输出的已打标评论列表，每条包含:
            - review_id: 评论唯一ID
            - title: 评论标题
            - body: 评论内容
            - rating: 评分 (1-5)
            - sentiment: 情感倾向
            - info_score: 信息密度评分 (1-20，代表"含金量")
            - tags: 22维度标签字典，如 {"场景_使用场景": "家用", "人群_性别": "女性"}

    Returns:
        Tuple:
            - personas: 画像列表，按人数降序，每个包含:
                {name, count, tags, dimension, color}
            - golden_samples: 黄金样本列表，每个包含:
                {review_id, body, rating, sentiment, sentiment_class, info_score,
                 tags, persona_name}

    Example:
        >>> personas, samples = analyze_user_personas(reviews)
        >>> personas[0]["name"]
        '家用_女性'
        >>> personas[0]["count"]
        45
        >>> len(samples)
        12  # 4个画像 x (3正+3负) = 最多 24 条样本，实际看画像数量和样本量
    """
    # 打标结果为空的保护
    if not tagged_reviews:
        return [], []

    # Step 1: 识别用户画像（核心逻辑在 _identify_personas 里）
    personas, dimension_name = _identify_personas(tagged_reviews)

    # Step 2: 为每个画像筛选最具代表性的评论样本
    golden_samples = _select_golden_samples(tagged_reviews, personas)

    return personas, golden_samples


def _identify_personas(reviews: List[Dict]) -> Tuple[List[Dict], str]:
    """
    识别用户画像（私有函数，包含维度退化逻辑）

    策略：用"场景_使用场景 + 人群_性别"的交叉组合作为画像名
    例如：{场景: "家用", 性别: "女性"} → 画像名 "家用_女性"

    为什么选这两个维度？
    - 场景：最能体现用户需求差异的维度（家用 vs 办公 vs 户外 完全不同）
    - 性别：最基础的人口统计维度，但"不明"比例可能很高
    - 两个交叉 = 场景+性别 组合画像，比单一维度更有区分度

    动态阈值逻辑：
    - > 100 条评论：至少 3 条才算一个画像（config.PERSONA_MIN_COUNT）
    - ≤ 100 条评论：门槛降到 2 条（小样本情况下保护画像不被吞掉）

    维度退化兜底：
    1. 先试 "场景 + 性别"（最强区分度）
    2. 不行就只用"场景"（性别大比例不明时的退路）
    3. 再不行只用"性别"
    4. 全不行就创建一个"全量用户"作为兜底画像

    Returns:
        Tuple:
            - 画像列表（按人数降序，最多 config.MAX_PERSONAS=4 个）
            - 使用的维度名称（用于日志）
    """
    # ── 逻辑 A: 动态阈值（小样本下降低门槛，防止画像被全过滤掉） ──
    total_samples = len(reviews)                                       # 总评论数
    min_count = 2 if total_samples <= 100 else config.PERSONA_MIN_COUNT  # ≤100条→2人即可成画像

    # ── 逻辑 B: 维度退化尝试序列（从强到弱兜底） ──
    # 每个元素: (维度显示名称, [要交叉的标签键列表])
    dimension_attempts = [
        ("场景_性别", ["场景_使用场景", "人群_性别"]),                  # 第一优先级：场景+性别
        ("场景", ["场景_使用场景"]),                                     # 退路1：仅场景
        ("性别", ["人群_性别"])                                          # 退路2：仅性别（一般不推荐，性别数据"不明"率太高）
    ]

    best_dimension = "全局"                                              # 最终实际使用的维度（兜底值）
    final_personas_raw = []                                              # 最终画像列表

    for dim_name, tag_keys in dimension_attempts:                       # 按优先级依次尝试
        persona_counter = Counter()                                      # 计数器：{画像名: 人数}
        persona_tag_stats = {}                                            # 每个画像内的标签统计

        for review in reviews:                                           # 遍历所有评论
            tags = review.get("tags", {})                                 # 取该评论的22维标签
            values = [tags.get(k, "不明") for k in tag_keys]             # 提取本维度需要的标签值
            # 过滤：如果需要的标签全是"不明/未提及/nan/None"，跳过
            if all(v in ["不明", "未提及", "nan", "None"] for v in values):
                continue

            p_name = " + ".join(values)                                   # 画像名如 "家用_女性" 或 "家用_不明"
            persona_counter[p_name] += 1                                   # 该画像人数 +1

            # 统计该画像内各标签的分布（用于展示画像特征）
            if p_name not in persona_tag_stats:
                persona_tag_stats[p_name] = {}
            for t_key, t_val in tags.items():                             # 遍历所有22维标签
                if t_val:                                                  # 只统计非空标签
                    if t_key not in persona_tag_stats[p_name]:
                        persona_tag_stats[p_name][t_key] = Counter()      # 初始化该标签的计数器
                    persona_tag_stats[p_name][t_key][t_val] += 1           # 该标签值 +1

        # 筛选满足最小人数门槛的画像
        valid = [
            (name, count) for name, count in persona_counter.most_common()  # most_common() = 按人数降序
            if count >= min_count                                          # 过滤掉人数太少的
        ]

        if valid:                                                          # 当前维度策略找到了有效画像 → 不再降级
            best_dimension = dim_name
            for idx, (name, count) in enumerate(valid[:config.MAX_PERSONAS]):  # 最多取 MAX_PERSONAS=4 个
                # 提取该画像的典型标签特征（每个标签取出现最多的值）
                typical_tags = {}
                for t_key, counter in persona_tag_stats.get(name, {}).items():
                    top_val, top_count = counter.most_common(1)[0]         # 取该标签下出现最多的值
                    # 附注实际有该特征的人数（而不是总人数），体现数据可解释性
                    typical_tags[t_key] = f"{top_val}(仅{top_count}人有此特征)"

                final_personas_raw.append({
                    "name": name,                                           # 画像名如 "家用_女性"
                    "count": count,                                         # 该画像的人数
                    "tags": typical_tags,                                   # 该画像的典型标签特征
                    "dimension": tag_keys                                    # 保存用于后续样本匹配的维度键
                })
            break                                                           # 找到了就退出，不继续降级

    # ── 兜底：所有维度策略都找不到有效画像 → 创建全局画像 ──
    if not final_personas_raw:
        final_personas_raw.append({
            "name": "全量用户",                                            # 没有分组就只有一个大画像
            "count": len(reviews),
            "tags": {},                                                     # 无分组特征
            "dimension": []
        })
        best_dimension = "全局综述"

    # ── 给每个画像分配一个颜色（轮流转，循环使用 PERSONA_COLORS） ──
    for idx, p in enumerate(final_personas_raw):
        p["color"] = PERSONA_COLORS[idx % len(PERSONA_COLORS)]            # 取余防止越界

    return final_personas_raw, best_dimension


def _select_golden_samples(
    reviews: List[Dict],
    personas: List[Dict]
) -> List[Dict]:
    """
    为每个画像筛选黄金样本（每画像取 info_score 最高的 3 正 + 3 负）

    黄金样本 = 信息含金量最高且情感明确的代表性评论，
    后续会直接嵌入到洞察报告和 HTML 看板中作为"用户原声"展示。

    筛选逻辑：
    1. 把评论按画像分组
    2. 每组分成正面和负面两类
    3. 同类内按 info_score 降序排列（信息量高的优先）
    4. 每画像各取前3条正面 + 前3条负面

    Args:
        reviews: 全部已打标评论
        personas: _identify_personas 返回的画像列表

    Returns:
        黄金样本列表，每个元素包含:
            {review_id, body, rating, sentiment, sentiment_class,
             info_score, tags, persona_name}
    """
    if not personas:                                                     # 没有画像就没有样本
        return []

    golden_samples = []
    for persona in personas:                                            # 遍历每个画像
        persona_name = persona["name"]                                   # 画像名如 "家用_女性"
        dim_keys = persona.get("dimension", [])                           # 该画像使用的标签键

        # ── 筛选属于该画像的评论 ──
        reviews_for_persona = []
        for r in reviews:
            if not dim_keys:                                              # 全局画像（兜底）→ 包含所有评论
                reviews_for_persona.append(r)
                continue

            tags = r.get("tags", {})
            # 用同样的维度键拼接出这条评论的画像名
            r_persona_name = " + ".join([tags.get(k, "不明") for k in dim_keys])
            if r_persona_name == persona_name:                             # 匹配成功
                reviews_for_persona.append(r)

        # ── 按情感分组并排序（info_score 高的排在前面） ──
        pos = sorted(
            [r for r in reviews_for_persona if r.get("sentiment") in POSITIVE_SENTIMENTS],
            key=lambda x: x.get("info_score", 0), reverse=True             # 按 info_score 降序
        )
        neg = sorted(
            [r for r in reviews_for_persona if r.get("sentiment") in NEGATIVE_SENTIMENTS],
            key=lambda x: x.get("info_score", 0), reverse=True             # 按 info_score 降序
        )

        # ── 取样：每画像取 3 正 + 3 负 ──
        for r in (pos[:3] + neg[:3]):                                     # 正面Top3 + 负面Top3
            sample = {
                "review_id": r.get("review_id"),                           # 评论ID
                "body": r.get("body", r.get("title", "")),                 # 评论正文（没正文用标题兜底）
                "rating": r.get("rating"),                                 # 评分
                "sentiment": r.get("sentiment"),                           # 情感标签
                "sentiment_class": SENTIMENT_CLASS_MAP.get(r.get("sentiment"), "neutral"),  # 前端CSS类
                "info_score": r.get("info_score", 0),                     # 信息密度评分
                "tags": r.get("tags", {}),                                 # 完整22维标签
                "persona_name": persona_name,                              # 所属画像名（便于追踪来源）
            }
            golden_samples.append(sample)

    return golden_samples


def get_persona_summary(personas: List[Dict]) -> str:
    """
    生成画像摘要文本（用于前端展示或日志）

    输出示例：
    "识别到 3 个用户画像：
     - 家用_女性: 45 条评论 (占比 50.0%)
     - 办公_男性: 30 条评论 (占比 33.3%)
     - 户外_不明: 15 条评论 (占比 16.7%)"

    Args:
        personas: 画像列表

    Returns:
        摘要文本
    """
    if not personas:
        return "未识别到有效用户画像（评论样本不足）"

    total = sum(p['count'] for p in personas)                              # 所有画像的总人数
    lines = [
        f"识别到 {len(personas)} 个用户画像：",
        ""
    ]

    for persona in personas:
        lines.append(
            f"- {persona['name']}: {persona['count']} 条评论 "
            f"(占比 {persona['count'] / total * 100:.1f}%)"               # 计算百分比
        )

    return "\n".join(lines)


def validate_sample_distribution(golden_samples: List[Dict]) -> Dict[str, int]:
    """
    验证样本分布是否均衡（用于质量检查）

    期望分布：每个画像 3 正 + 3 负，总体正负均衡

    Args:
        golden_samples: 黄金样本列表

    Returns:
        统计信息:
            {total: 总数, positive: 正面数, negative: 负面数, neutral: 中立数}
    """
    if not golden_samples:
        return {"total": 0, "positive": 0, "negative": 0}

    # 统计正面数量
    positive_count = sum(
        1 for s in golden_samples
        if s.get("sentiment") in POSITIVE_SENTIMENTS
    )
    # 统计负面数量
    negative_count = sum(
        1 for s in golden_samples
        if s.get("sentiment") in NEGATIVE_SENTIMENTS
    )

    return {
        "total": len(golden_samples),
        "positive": positive_count,
        "negative": negative_count,
        "neutral": len(golden_samples) - positive_count - negative_count,  # 剩下的就是中立的
    }
