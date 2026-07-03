#!/usr/bin/env python3                                          # 告诉系统用 python3 执行此脚本
"""
Amazon 商品评论 AI 深度分析工具 - 主入口 V2.0 (Agent 原生版)
功能：支持交互式向导 + 全参数驱动 + Sorftime数据对接 + 多模板看板 + 飞书同步
"""

import sys                                                      # 系统函数：退出程序、获取命令行参数
import argparse                                                 # 命令行参数解析器（处理 --source --asin 等）
import re                                                       # 正则表达式（用于提取 ASIN）
import os                                                       # 操作系统接口（环境变量等）
from pathlib import Path                                        # 面向对象的文件路径处理
from datetime import datetime                                   # 日期时间处理
import pandas as pd                                             # 数据分析库（读写 CSV/Excel）
from dotenv import load_dotenv, find_dotenv                     # 加载 .env 环境变量文件

# 加载 .env 环境变量（从当前目录向上搜索，确保无论从哪个目录运行都能找到）
load_dotenv(find_dotenv())

# 导入核心模块（src/ 目录下各功能模块）
from src.data_loader import load_reviews_from_file, download_if_url  # CSV 加载器 + URL 下载
from src.review_analyzer import analyze_all                          # Phase 1：AI 打标引擎
from src.user_persona_analyzer import analyze_user_personas          # Phase 2：用户画像识别
from src.insights_generator import calculate_stats_summary, generate_insights  # Phase 3：洞察报告生成
from src.config import config                                        # 全局配置单例

# V2.0 新模块
from src.data_fetchers import get_fetcher, list_fetchers             # 数据接入层（Sorftime / CSV）
from src.output_manager import OutputManager                         # Phase 4：统一输出管理
from src.prompts.manager import list_chapters                        # 13 章 Prompt 管理器


def print_intro():
    """打印工具详细说明（启动 banner）"""
    print("""
🚀 多场景评论内容 AI 深度分析工具 V2.0 — Agent 原生版 Created By Buluu@新西楼
======================================================================
核心功能: 22维度智能标签 · 14章深度洞察报告 · 多风格可视化看板
数据来源: 本地CSV / Sorftime平台
输出方式: MD报告 + HTML看板(多模板) + 飞书同步(可选)
======================================================================
    """)


def config_wizard(total_available: int,
                  preset_max=None, preset_creator=None):
    """
    交互式配置向导（强制交互模式）
    当用户没有通过命令行提供完整参数时，用问答方式收集参数

    Args:
        total_available: 可用的评论总数（文件里一共多少条）
        preset_max: 预设的分析数量（来自 --max-reviews 参数，可能是 None）
        preset_creator: 预设的署名（来自 --creator 参数，可能是 None）

    Returns:
        tuple: (max_reviews, creator) 分析数量和署名
    """

    # Q1：问用户要分析多少条评论（打标深度）
    print(f"🚀 欢迎使用电商评论AI深度洞察器 (V2.0 Created By Buluu@新西楼)")
    print(f"📦 [向导 1/2] 文件共有 {total_available} 条有效评论，您计划打标分析多少条？")
    if preset_max is not None:                                 # 如果命令行已经给了 --max-reviews
        print(f"   [当前预设: {preset_max} 条]")
        max_rev_input = input(f"   请输入数量 (直接回车使用预设值 {preset_max} 条) >>> ").strip()
        max_rev = int(max_rev_input) if max_rev_input else preset_max  # 用户输入了就用输入的，否则用预设
    else:                                                      # 命令行没给，用默认值 100
        print("   [默认值: 100 条，建议 100-300]")
        max_rev_input = input("   请输入数量 (直接回车使用默认值 100 条) >>> ").strip()
        max_rev = int(max_rev_input) if max_rev_input else 100      # 用户输入了就用输入的，否则用 100
    # 确保用户要的数量不超过实际可用的评论数
    max_rev = min(max_rev, total_available)

    # Q2：问用户报告署名（显示在 HTML 看板上的作者名）
    print("\n✍️ [向导 2/2] 报告需要个性化署名吗？")
    if preset_creator is not None:                             # 如果命令行已经给了 --creator
        print(f"   [当前预设: {preset_creator}]")
        creator_input = input(f"   请输入署名 (直接回车使用预设值 '{preset_creator}') >>> ").strip()
        creator = creator_input if creator_input else preset_creator  # 用户输入了就用输入的，否则用预设
    else:                                                      # 命令行没给，留空默认为 None
        print("   [留空默认为: AI Assistant]")
        creator_input = input("   请输入署名 (直接回车使用默认值) >>> ").strip()
        creator = creator_input if creator_input else None          # 用户输入了就用输入的，否则 None

    # 打印用户选择的配置确认信息
    print("\n" + "=" * 60)
    print("✅ 配置确认：")
    print(f"   📊 分析数量: {max_rev} 条")
    print(f"   🤖 运行模式: CLI 本地模式")
    print(f"   ✍️  报告署名: {creator or 'AI Assistant'}")
    print("=" * 60 + "\n")

    return (max_rev, creator)                                  # 返回两个值：分析数量、署名


def save_tagged_reviews_to_csv(tagged_reviews: list, asin: str) -> Path:
    """
    将 AI 打标后的评论数据保存为 CSV 文件
    每个标签维度成为一个独立的列（如"人群_性别: 男"）

    Args:
        tagged_reviews: 打标后的评论列表，每条评论文含有 tags 字段
        asin: 产品 ASIN 码（用于生成文件名）

    Returns:
        Path: 保存的 CSV 文件路径
    """
    flattened_reviews = []                                     # 扁平化后的数据列表（一条评论文一行）
    for review in tagged_reviews:                              # 遍历每条打标后的评论
        original_data = review.get("_original_data", {})        # 获取原始 CSV 数据（评论正文、评分等）
        flat_row = dict(original_data)                          # 复制原始数据到新行
        tags = review.get("tags", {})                           # 获取 AI 打的 22 维度标签
        for tag_key, tag_value in tags.items():                 # 遍历每个标签维度
            if tag_key != "情感_总体评价":                       # 跳过"情感_总体评价"（最后单独处理，确保在末尾列）
                flat_row[tag_key] = tag_value                   # 添加标签值作为新列，列名如"人群_性别"
        flat_row["情感_总体评价"] = tags.get("情感_总体评价", "")  # 把"情感_总体评价"放到最后列
        flat_row["评论价值打分"] = review.get("info_score", 0)   # 添加评论信息价值评分
        flat_row["打标时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 记录打标时间戳
        flattened_reviews.append(flat_row)                      # 加入扁平化列表

    df = pd.DataFrame(flattened_reviews)                       # 用 pandas 把列表转成 DataFrame
    csv_path = config.get_csv_path(asin)                        # 根据 ASIN 生成输出路径
    df.to_csv(csv_path, index=False, encoding=config.CSV_ENCODING)  # 导出 CSV，不含行号，UTF-8 编码
    return csv_path                                            # 返回文件路径


def extract_asin_from_file(file_path: str) -> str:
    """
    从文件名提取 ASIN（亚马逊标准识别码，10位大写字母数字组合）
    例如：B0C123ABCD_reviews.csv → B0C123ABCD

    Args:
        file_path: 输入文件路径

    Returns:
        str: 提取到的 ASIN，如果提取不到则取文件名前10位
    """
    filename = Path(file_path).stem                             # 取文件名（不含扩展名）
    asin_pattern = r'[A-Z0-9]{10}'                              # 正则：10位大写字母或数字
    matches = re.findall(asin_pattern, filename.upper())        # 转大写后匹配所有符合模式的字符串
    return matches[0] if matches else filename.upper()[:10]     # 有匹配就返回第一个，没有就取前10位


def is_interactive_environment():
    """检测是否在交互式终端中运行（用户能输入参数）"""
    return sys.stdin.isatty()                                  # isatty() = True 表示连接到终端，False 表示被管道/脚本调用


def main():
    """主函数：整个分析流程的入口"""

    # 1. 解析命令行参数 --------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Amazon Review Analyzer V2.0 — Agent 原生版")
    parser.add_argument("input_file", nargs="?", default=None, help="输入 CSV/Excel 文件路径或 URL（使用 --source sorftime 时可省略）") # 位置参数：输入文件路径（可选）
    # V2.0: 数据来源相关参数
    parser.add_argument("--source", choices=["csv", "sorftime"], default="csv", help="数据来源: csv(默认) 或 sorftime") # 数据来源选择
    parser.add_argument("--asin", help="产品 ASIN（--source sorftime 时必填）")  # 亚马逊产品码
    parser.add_argument("--site", default="US", help="站点代码（默认 US，可选 UK/DE/JP 等）") # 亚马逊站点
    # V2.0: 模板与输出参数
    parser.add_argument("--template", default="premium-gold", help="可视化看板模板名称（默认 premium-gold，传 none 跳过HTML生成）") # 可视化模板选择
    parser.add_argument("--feishu-sync", action="store_true", help="同步结果到飞书文档（需要 lark-cli）") # 是否同步到飞书
    # 原有参数
    parser.add_argument("--engine", choices=["claude", "opencode"], default=None, help="CLI 引擎: claude (默认) 或 opencode") # CLI 引擎选择
    parser.add_argument("--max-reviews", type=int, help="分析评论上限", default=None)  # 分析数量
    parser.add_argument("--batch-size", type=int, default=20, help="批次大小")       # 每批处理条数
    parser.add_argument("--concurrent", type=int, default=None, help="最大并发批次数 (默认4, 上限8)") # 并发批次数
    parser.add_argument("--creator", help="报告署名/品牌", default=None)              # 报告署名
    parser.add_argument("--output-dir", help="自定义输出目录")                        # 自定义输出目录
    args = parser.parse_args()                                     # 执行解析，得到参数对象

    # 2. 参数校验 --------------------------------------------------------------------
    if args.source == "sorftime" and not args.asin:                # Sorftime 模式必须有 ASIN
        parser.error("--source sorftime 需要 --asin 参数")
    if args.source == "csv" and not args.input_file:               # CSV 模式必须有输入文件
        parser.error("CSV 模式需要提供输入文件路径")

    # 判断是否缺少关键参数（没给 --max-reviews 或没给 --creator）
    _missing_params = []                                           # 记录缺少的参数名
    if args.max_reviews is None:                                   # 没有指定分析数量
        _missing_params.append("--max-reviews")
    if args.creator is None:                                       # 没有指定署名
        _missing_params.append("--creator")
    needs_interaction = len(_missing_params) > 0                   # 缺参数就需要交互模式

    # 非交互环境 + 缺少参数 → 拒绝执行，报错退出（不给 LLM/Agent 猜测的机会）
    if needs_interaction and not is_interactive_environment():     # 条件：缺参数 AND 没有终端（如被脚本调用）
        print("=" * 70)
        print("❌ 缺少必要参数，无法在非交互式环境中运行")
        print("=" * 70)
        print()
        print("  缺少以下参数：")
        for p in _missing_params:                                  # 逐条列出缺少的参数
            print(f"    ⚠️  {p}")
        print()
        print("  请通过命令行提供完整参数：")
        print(f"    python3 main.py '{args.input_file}' \\")
        print("      --max-reviews 100 \\")
        print("      --creator '你的署名'")
        print()
        print("  💡 提示：如需使用交互式菜单，请直接在终端中运行此命令。")
        print("=" * 70)
        sys.exit(1)                                                # 以错误码退出

    # 3. 打印工具说明 ----------------------------------------------------------------
    print_intro()

    # 4. 处理 --engine 参数（用户可覆盖自动探测的 CLI 引擎）--------------------------
    if args.engine:                                                # 如果用户指定了引擎
        config.CLI_ENGINE = args.engine                            # 覆盖配置中的自动探测结果
        print(f"🔧 CLI 引擎: {config.CLI_ENGINE}")

    # 5. Phase 1: 数据获取 ---------------------------------------------------------
    # V2.0：支持两种数据来源——Sorftime 平台 或 本地 CSV
    if args.source == "sorftime":                                  # 模式 A：从 Sorftime 获取
        print(f"\n📡 [Phase 1/5] 从 Sorftime 获取评论数据...")
        print(f"   ASIN: {args.asin}, 站点: {args.site}")
        fetcher = get_fetcher("sorftime")                          # 工厂方法获取 Sorftime 采集器
        if not fetcher.validate_config():                          # 验证配置（API Key 是否设置）
            print("❌ Sorftime 配置无效。请设置 SORFTIME_API_KEY 环境变量。")
            sys.exit(1)
        try:
            csv_path_str = fetcher.fetch(args.asin, fields=None, site=args.site)  # 拉取评论数据，返回 CSV 路径
            resolved_file = csv_path_str                           # 拿到的 CSV 作为后续分析的输入
            print(f"✅ 数据获取完成: {csv_path_str}")
        except Exception as e:                                     # 拉取失败则退出
            print(f"❌ Sorftime 数据获取失败: {e}")
            sys.exit(1)
    else:                                                          # 模式 B：本地 CSV/URL
        # 原有 CSV 路径
        if not args.input_file:                                    # 双重保险：再检查一次文件路径
            print("❌ CSV 模式需要提供输入文件路径")
            sys.exit(1)
        resolved_file = download_if_url(args.input_file)           # 如果是 URL 则先下载，否则直接返回路径

    # 6. 检查文件是否存在 -------------------------------------------------------------
    input_path = Path(resolved_file)                               # 字符串转 Path 对象
    if not input_path.exists():                                    # 文件不存在报错
        print(f"❌ 错误：找不到文件: {input_path}")
        sys.exit(1)

    # 7. 加载数据、预处理 --------------------------------------------------------------------
    # 预处理：列名模糊匹配，去除空值、空行、评论过短的。
    reviews, original_df = load_reviews_from_file(resolved_file)   # 加载 CSV，返回评论列表和原始 DataFrame
    total_available = len(reviews)                                 # 记录一共有多少条有效评论
    print(f"📄 成功加载表格：检测到 {total_available} 条有效评论记录")

    # 8. 配置合并（优先级：命令行 > 向导 > 默认值）------------------------------------
    if not needs_interaction:                                      # 命令行已经给了全部参数
        # 两个参数都已通过命令行提供，跳过向导
        print(f"\n✅ 检测到完整命令行参数，跳过交互式向导")
        max_reviews = args.max_reviews                             # 直接用命令行参数
        creator = args.creator
    else:                                                          # 缺参数，需要交互式问答
        # 在 TTY 环境且缺少参数 → 启动交互式向导
        wizard_max_reviews, wizard_creator = config_wizard(        # 调用交互式配置向导
            total_available=total_available,
            preset_max=args.max_reviews,                            # 给定的参数作为预设值传入
            preset_creator=args.creator
        )
        print()                                                     # 向导结束后添加空行
        # 向导结果优先（向导中用户的选择覆盖命令行预设）
        max_reviews = wizard_max_reviews
        creator = wizard_creator

    # 9. 应用配置到全局 config 对象 ------------------------------------------------
    if max_reviews:
        config.MAX_REVIEWS = max_reviews                            # 设置分析数量上限

    if creator:
        config.HTML_CREATOR_NAME = creator                          # 设置 HTML 看板上的署名

    # 并发数配置
    if args.concurrent:
        config.MAX_CONCURRENT_AGENTS = args.concurrent              # 用户可自定义并发线程数，默认为4

    # 引擎名称展示（用于输出版本信息）
    engine_label = "OpenCode" if config.CLI_ENGINE == "opencode" else "Claude CLI"
    print(f"💡 模式：{engine_label} 本地模式 (全本地方案)")
    print(f"🔧 并发线程数: {config.MAX_CONCURRENT_AGENTS}")

    # 10. 应用自定义输出目录 ----------------------------------------------------------
    if args.output_dir:                                            # 用户指定了输出目录
        output_path = Path(args.output_dir)
        if output_path.exists() and output_path.is_file():         # 检查是否是一个文件（而不是目录）
            print(f"❌ 错误：输出路径是一个文件，不是目录: {output_path}")
            sys.exit(1)
        config.OUTPUT_DIR = output_path                             # 覆盖配置中的输出目录
        # 确保输出目录存在
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)       # 不存在则创建
        print(f"📁 自定义输出目录: {config.OUTPUT_DIR}")

    # 11. 提取 ASIN -----------------------------------------------------------------
    asin = args.asin if args.source == "sorftime" else extract_asin_from_file(resolved_file)  # Sorftime用参数值，CSV从文件名提取（如果提取不到则取文件名前10位）

    # 12. 截断评论（如果实际数量超过分析上限）------------------------------------------
    if len(reviews) > config.MAX_REVIEWS:
        print(f"✂️  评论总数 {len(reviews)} 超过上限，截取前 {config.MAX_REVIEWS} 条")
        reviews = reviews[:config.MAX_REVIEWS]                      # 只取前 N 条

    try:
        # ========== 执行全流程（Phase 2→3→4→5）==========

        # Phase 2: AI 深度打标分析 --------------------------------------------------
        # 将评论分批，每批并发调用 Claude/OpenCode CLI，给每条评论打上 22 维度标签
        print(f"\n🧠 [Phase 2/5] 评论AI深度打标分析中...")
        tagged_reviews = analyze_all(reviews, batch_size=args.batch_size)  # 执行打标，返回带标签的评论列表
        print(f"✅ [Phase 2/5] 评论打标完成！成功分析 {len(tagged_reviews)} 条评论\n")

        # Phase 3: 用户画像识别 -----------------------------------------------------
        # 根据已打标的评论，按"使用场景+性别"聚类用户画像，每画像选3正3负样本
        print(f"👥 [Phase 3/5] 用户画像识别与降级逻辑配置中...")
        print(f"   - 正在分析 {len(tagged_reviews)} 条打标评论...")
        print(f"   - 识别用户画像中...")
        personas, golden_samples = analyze_user_personas(tagged_reviews)  # 返回画像列表和黄金样本
        print(f"✅ [Phase 3/5] 用户画像识别完成！识别到 {len(personas)} 个画像，{len(golden_samples)} 条黄金样本\n")

        # Phase 4: AI 撰写深度战略洞察报告 -----------------------------------------
        # 先把打标结果做统计汇总，再把统计+画像+样本传给 CLI，生成 14 章 Markdown 报告
        print(f"📝 [Phase 4/5] AI深度战略洞察报告生成中...")
        print(f"   - 正在生成 {len(personas)} 个用户画像分析...")
        print(f"   - 使用引擎: {engine_label}")
        stats = calculate_stats_summary(tagged_reviews)               # 统计汇总：情感分布、标签TOP30、维度统计等
        insights_md = generate_insights(                               # 调用 CLI 生成 Markdown 洞察报告
            stats=stats,
            personas=personas,
            golden_samples=golden_samples,
            asin=asin
        )
        if insights_md:                                                # 报告生成成功
            print(f"✅ [Phase 4/5] 洞察报告已生成！字数约 {len(insights_md):,} 字\n")
        else:                                                          # 报告生成失败
            print(f"⚠️ [Phase 4/5] 洞察报告生成失败\n")

        # 保存 Markdown 报告到文件
        md_path = config.get_md_path(asin)                             # 根据 ASIN 生成 MD 输出路径
        if insights_md:
            with open(md_path, 'w', encoding='utf-8') as f:           # 以 UTF-8 编码写入
                f.write(insights_md)

        # 保存打标后的 CSV 数据
        csv_path = save_tagged_reviews_to_csv(tagged_reviews, asin)   # 调用前面定义的函数，导出打标结果

        # Phase 5: 输出管理 — 统一生成 MD + HTML看板 + 飞书同步 ----------
        print(f"📦 [Phase 5/5] 生成完整输出包...")
        from src.output_manager import generate_outputs, select_template  # 导入输出管理器

        # 选择模板（none 表示跳过 HTML 生成）
        template_name = args.template                                  # 用户通过 --template 指定的模板名
        if template_name.lower() == "none":                            # 如果传了 "none"
            template_name = None                                       # 设 None 表示跳过 HTML 看板
        else:
            # 如果模板不存在，自动回退到第一个可用模板
            try:
                from src.template_engine import list_templates as _lt   # 列出所有可用模板
                available = [t["name"] for t in _lt()]                 # 提取模板名列表
                if template_name not in available:                     # 用户指定的模板不存在
                    print(f"   ⚠️ 模板 '{template_name}' 不存在，使用默认模板")
                    template_name = available[0] if available else "premium-gold"  # 用第一个可用的
            except Exception:                                          # 列出模板失败也不阻塞流程
                pass

        # 构建统计摘要（给 OutputManager 用的结构化数据）
        summary = {
            "total": len(tagged_reviews),                              # 总评论数
            "tagged": stats["tagged"],                                 # 成功打标数
            "persona_count": len(personas),                            # 画像数量
            "avg_rating": stats.get("avg_rating", 0),                  # 平均评分
            "sentiment": stats.get("sentiment", {}),                   # 情感分布（正面/中性/负面）
            "top_tags": stats.get("top_tags", {})                      # TOP 标签
        }

        # 准备完整的分析数据包，传给 output_manager
        analysis_data_for_output = {
            "asin": asin,                                              # 产品 ASIN
            "product_name": asin,                                      # 产品名称（暂用 ASIN 代替）
            "total_reviews": len(tagged_reviews),                      # 总评论数
            "avg_rating": stats.get("avg_rating", 0),                  # 平均评分
            "summary": summary,                                        # 统计摘要
            "sentiment": stats.get("sentiment", {}),                   # 情感分布
            "sentiment_distribution": stats.get("sentiment", {}),      # 情感分布（别名）
            "tag_statistics": stats.get("top_tags", {}),               # 标签统计
            "top_tags": stats.get("top_tags", {}),                     # TOP标签（别名）
            "dimensional_stats": stats.get("dimensional_stats", {}),   # 各维度统计
            "personas": [{"name": p.get("name", ""), "count": p.get("count", 0), "tags": p.get("tags", {})} for p in personas],  # 画像列表（提取关键字段）
            "golden_samples": golden_samples,                          # 黄金样本（3正+3负 每画像）
            "insights_md": insights_md,                                # Markdown 洞察报告原文
            "statistics": stats,                                       # 完整统计数据
        }

        # 输出配置
        output_config = {
            "template_name": template_name,                            # 模板名（None=跳过HTML）
            "sync_feishu": args.feishu_sync,                           # 是否同步飞书
            "output_dir": str(config.OUTPUT_DIR),                      # 输出目录
            "asin": asin,                                              # 产品码
            "creator": config.HTML_CREATOR_NAME,                       # 署名
        }

        # 执行输出：写 MD、渲染 HTML、可选飞书同步
        output_results = generate_outputs(analysis_data_for_output, output_config)

        # 飞书同步结果展示
        feishu_result = output_results.get("feishu_result", {})       # 获取同步结果
        if args.feishu_sync:                                           # 用户开启了飞书同步
            if feishu_result and feishu_result.get("success"):         # 同步成功
                print(f"   ✅ 飞书同步成功！")
                if feishu_result.get("doc_url"):                       # 打印飞书文档链接
                    print(f"   📄 文档: {feishu_result['doc_url']}")
                wb_count = feishu_result.get("whiteboard_count", 0)   # 打印白板图表数量
                if wb_count > 0:
                    print(f"   📊 白板图表: {wb_count} 个已渲染")
            else:                                                      # 同步失败但不影响本地输出
                error = feishu_result.get("error", "未知错误") if feishu_result else "同步失败"
                print(f"   ⚠️ 飞书同步失败: {error}")
                print(f"   💡 本地文件已安全生成，不影响使用")

        # 最终输出结果汇总
        final_md = output_results.get("md_path", str(md_path))         # MD 报告路径
        final_html = output_results.get("html_path", "")               # HTML 看板路径

        # 打印完整成果 --------------------------------------------------------------
        print("\n" + "✨" * 30)                                        # 分隔线
        print("🎉 分析任务圆满完成！")
        print(f"  - 洞察报告: {Path(final_md).name}")                  # 只显示文件名
        print(f"  - 结构数据: {csv_path.name}")                        # CSV 文件名
        if final_html:                                                 # 如果生成了 HTML 看板
            print(f"  - 可视化看板: {Path(final_html).name} (模板: {template_name})")
        else:                                                          # 如果跳过了 HTML
            print(f"  - 可视化看板: 已跳过")
        if args.feishu_sync and feishu_result and feishu_result.get("doc_url"):  # 如果同步了飞书
            print(f"  - 飞书文档: {feishu_result['doc_url']}")
            wb_count = feishu_result.get("whiteboard_count", 0)
            if wb_count > 0:
                print(f"  - 白板图表: {wb_count} 个")
        print("✨" * 30 + "\n")

    except Exception as e:                                             # 捕获任何未预期的异常
        print(f"\n❌ 引擎崩溃: {e}")
        import traceback                                               # 打印完整堆栈以便调试
        traceback.print_exc()
        sys.exit(1)                                                    # 异常退出


if __name__ == "__main__":                                             # Python 入口点：当直接运行此文件时执行 main()
    main()
