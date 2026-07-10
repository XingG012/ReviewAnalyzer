"""
Streamlit 分析管道 — 封装 5 Phase 分析流程

复用 review-analyzer-skill/src/ 的现有模块，不重复实现。
run_analysis_with_progress() 是生成器模式，每完成一步 yield 进度事件。
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import pandas as pd

# 将分析引擎加入模块搜索路径
_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "review-analyzer-skill"
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

# 统一输出目录到项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_ROOT = _PROJECT_ROOT / "output"
_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

from src.config import config                                                # noqa: E402
from src.data_loader import load_reviews_from_file                           # noqa: E402
from src.review_analyzer import analyze_all                                  # noqa: E402
from src.user_persona_analyzer import analyze_user_personas                  # noqa: E402
from src.insights_generator import calculate_stats_summary, generate_insights  # noqa: E402
from src.output_manager import generate_outputs                              # noqa: E402

# Phase 名称和 emoji
_PHASES = [
    (1, "📄 加载数据", 0, 20),
    (2, "🏷️ AI 打标", 20, 40),
    (3, "👥 用户画像", 40, 60),
    (4, "📝 洞察报告", 60, 80),
    (5, "📦 生成看板", 80, 100),
]


def run_analysis_with_progress(
    csv_path: str,
    asin: str = "UNKNOWN",
    max_reviews: int = 100,
    batch_size: int = 20,
    template: str = "premium-gold",
    creator: str = "Xing",
) -> Generator[Dict[str, Any], None, None]:
    """执行完整 5 Phase 分析流程（生成器模式）

    每次 yield 一个进度事件:
        {"phase": int, "msg": str, "pct": int, "done": bool, "result": dict|None}

    最终事件包含 result 字典。
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
        # ── 输出目录 ──────────────────────────────────────
        now = datetime.now()
        date_part = f"{now.month}.{now.day}-{now.hour:02d}:{now.minute:02d}"
        # 未知 ASIN 时用 CSV 文件名
        if asin == "UNKNOWN":
            csv_name = Path(csv_path).stem
            run_dir = _OUTPUT_ROOT / f"{csv_name}-{date_part}"
        else:
            run_dir = _OUTPUT_ROOT / f"{asin}-{date_part}"
        run_dir.mkdir(parents=True, exist_ok=True)
        config.OUTPUT_DIR = run_dir
        config.MAX_REVIEWS = max_reviews
        config.HTML_CREATOR_NAME = creator

        # ── Phase 1: 加载数据 ──────────────────────────────────
        yield {"phase": 1, "msg": "正在加载评论数据...", "pct": 5}
        reviews, _ = load_reviews_from_file(csv_path)
        result["total_reviews"] = len(reviews)

        if len(reviews) > max_reviews:
            reviews = reviews[:max_reviews]

        yield {
            "phase": 1, "msg": f"已加载 {len(reviews)} 条评论", "pct": 20,
        }

        # ── Phase 2: AI 打标 ──────────────────────────────────
        yield {"phase": 2, "msg": f"正在 AI 打标... (0/{len(reviews)})", "pct": 20}
        tagged_reviews = analyze_all(reviews, batch_size=batch_size)
        if not tagged_reviews:
            raise RuntimeError("打标结果为空")

        yield {
            "phase": 2, "msg": f"打标完成 ({len(tagged_reviews)}/{len(reviews)})", "pct": 40,
        }

        # ── Phase 3: 用户画像 ─────────────────────────────────
        yield {"phase": 3, "msg": "正在识别用户画像（场景×性别交叉）...", "pct": 40}
        personas, golden_samples = analyze_user_personas(tagged_reviews)
        result["persona_count"] = len(personas)

        yield {
            "phase": 3, "msg": f"识别到 {len(personas)} 个用户画像，{len(golden_samples)} 条黄金样本",
            "pct": 60,
        }

        # ── Phase 4: 洞察报告 ─────────────────────────────────
        yield {"phase": 4, "msg": "正在生成 14 章洞察报告...", "pct": 60}
        stats = calculate_stats_summary(tagged_reviews)
        insights_md = generate_insights(
            stats=stats, personas=personas,
            golden_samples=golden_samples, asin=asin,
        )

        md_path = config.get_md_path(asin)
        if insights_md:
            md_path.write_text(insights_md, encoding="utf-8")
            result["md_path"] = str(md_path)

        yield {
            "phase": 4, "msg": f"报告已生成 ({len(insights_md or ''):,} 字)", "pct": 80,
        }

        # 保存打标 CSV
        csv_out = config.get_csv_path(asin)
        pd.DataFrame(tagged_reviews).to_csv(csv_out, index=False, encoding="utf-8-sig")
        result["csv_out_path"] = str(csv_out)

        # ── Phase 5: 输出看板 ─────────────────────────────────
        yield {"phase": 5, "msg": "正在渲染可视化看板...", "pct": 80}
        analysis_data: Dict[str, Any] = {
            "asin": asin,
            "total_reviews": len(tagged_reviews),
            "personas": [
                {"name": p.get("name", ""), "count": p.get("count", 0), "tags": p.get("tags", {})}
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

        yield {
            "phase": 5, "msg": "✅ 全部完成", "pct": 100,
            "done": True, "result": result,
        }

    except FileNotFoundError as e:
        msg = f"未检测到 Claude Code CLI，请先安装：npm i -g @anthropic-ai/claude-code\n详情: {e}"
        result["error"] = msg
        yield {"phase": 0, "msg": msg, "pct": 0, "done": True, "result": result}
    except OSError as e:
        msg = f"磁盘空间不足或文件写入失败\n详情: {e}"
        result["error"] = msg
        yield {"phase": 0, "msg": msg, "pct": 0, "done": True, "result": result}
    except RuntimeError as e:
        msg = str(e)
        result["error"] = msg
        yield {"phase": 0, "msg": f"❌ {msg}", "pct": 0, "done": True, "result": result}
    except Exception as e:
        msg = f"分析失败: {e}"
        result["error"] = msg
        yield {"phase": 0, "msg": msg, "pct": 0, "done": True, "result": result}


# 向后兼容的同步版本
def run_analysis(**kwargs) -> Dict[str, Any]:
    """同步版本（兼容旧调用）"""
    final = None
    for event in run_analysis_with_progress(**kwargs):
        if event.get("done"):
            final = event.get("result", {})
    return final or {"success": False, "error": "未知错误"}
