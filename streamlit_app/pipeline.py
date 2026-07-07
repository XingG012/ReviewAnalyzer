"""
Streamlit 分析管道 — 封装 5 Phase 分析流程

复用 review-analyzer-skill/src/ 的现有模块，不重复实现。
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# 将分析引擎加入模块搜索路径
_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "review-analyzer-skill"
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

# 统一输出目录到项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_ROOT = _PROJECT_ROOT / "output"
_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

from src.config import config
from src.data_loader import load_reviews_from_file
from src.review_analyzer import analyze_all
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.output_manager import generate_outputs


def run_analysis(
    csv_path: str,
    asin: str = "UNKNOWN",
    max_reviews: int = 100,
    batch_size: int = 20,
    template: str = "premium-gold",
    creator: str = "Xing",
) -> Dict[str, Any]:
    """执行完整 5 Phase 分析流程

    Args:
        csv_path:    评论 CSV 文件路径
        asin:        产品 ASIN（从文件名提取或用户输入）
        max_reviews: 分析数量上限
        batch_size:  打标批次大小
        template:    HTML 看板模板名
        creator:     报告署名

    Returns:
        {
            "success": bool,
            "md_path": str,        # Markdown 报告路径
            "html_path": str,      # HTML 看板路径
            "csv_out_path": str,   # 打标 CSV 路径
            "total_reviews": int,  # 评论总数
            "persona_count": int,  # 画像数量
            "error": str,          # 错误信息（失败时）
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "md_path": "",
        "html_path": "",
        "csv_out_path": "",
        "total_reviews": 0,
        "persona_count": 0,
        "error": "",
    }

    try:
        # ── 每次分析独立目录: {ASIN}-{月}.{日}-{时}:{分} ────
        from datetime import datetime
        now = datetime.now()
        run_dir = _OUTPUT_ROOT / f"{asin}-{now.month}.{now.day}-{now.hour:02d}:{now.minute:02d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        config.OUTPUT_DIR = run_dir

        # ── Phase 1: 加载数据 ──────────────────────────────
        reviews, _ = load_reviews_from_file(csv_path)
        result["total_reviews"] = len(reviews)

        if len(reviews) > max_reviews:
            reviews = reviews[:max_reviews]

        config.MAX_REVIEWS = max_reviews
        config.HTML_CREATOR_NAME = creator

        # ── Phase 2: AI 打标 ──────────────────────────────
        tagged_reviews = analyze_all(reviews, batch_size=batch_size)
        if not tagged_reviews:
            raise RuntimeError("打标结果为空")

        # ── Phase 3: 用户画像 ──────────────────────────────
        personas, golden_samples = analyze_user_personas(tagged_reviews)
        result["persona_count"] = len(personas)

        # ── Phase 4: 洞察报告 ──────────────────────────────
        stats = calculate_stats_summary(tagged_reviews)
        insights_md = generate_insights(
            stats=stats,
            personas=personas,
            golden_samples=golden_samples,
            asin=asin,
        )

        md_path = config.get_md_path(asin)
        if insights_md:
            md_path.write_text(insights_md, encoding="utf-8")
            result["md_path"] = str(md_path)

        # 保存打标 CSV
        csv_out = config.get_csv_path(asin)
        pd.DataFrame(tagged_reviews).to_csv(csv_out, index=False, encoding="utf-8-sig")
        result["csv_out_path"] = str(csv_out)

        # ── Phase 5: 输出看板 ──────────────────────────────
        analysis_data = {
            "asin": asin,
            "total_reviews": len(tagged_reviews),
            "personas": [
                {
                    "name": p.get("name", ""),
                    "count": p.get("count", 0),
                    "tags": p.get("tags", {}),
                }
                for p in personas
            ],
            "golden_samples": golden_samples,
            "insights_md": insights_md or "",
            "statistics": stats,
            "sentiment": stats.get("sentiment", {}),
            "sentiment_distribution": stats.get("sentiment", {}),
            "top_tags": stats.get("top_tags", {}),
            "tag_statistics": stats.get("top_tags", {}),
            "avg_rating": stats.get("avg_rating", 0),
            "summary": {"total": len(tagged_reviews)},
        }

        output_config = {
            "template_name": template,
            "sync_feishu": False,
            "output_dir": str(config.OUTPUT_DIR),
            "asin": asin,
            "creator": creator,
        }

        outputs = generate_outputs(analysis_data, output_config)
        result["html_path"] = outputs.get("html_path", "")
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result
