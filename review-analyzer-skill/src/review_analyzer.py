"""
AI 分析引擎模块 V1.0 - CLI 原生版

重大变更：彻底移除第三方 API 依赖
- 移除 google.generativeai (Gemini API)
- 移除 Anthropic API 直接调用
- 改用 Python subprocess 调用宿主系统的 Claude Code CLI (claude -p)
- 所有 AI 推理通过 CLI 进行，使用您的 Claude 配额
"""

import json                                                            # JSON 解析：CLI 返回的 JSON 响应
import logging                                                         # 日志记录：取代 print，支持级别过滤
import os                                                              # 操作系统接口：环境变量传递
import shutil                                                          # Shell 工具：检查 CLI 命令是否存在
import subprocess                                                      # 子进程调用：执行 claude/opencode 命令
import time                                                            # 计时：统计各批次处理耗时
import threading                                                       # 线程：记录当前线程名用于日志
from concurrent.futures import ThreadPoolExecutor, as_completed         # 线程池：并发执行多个批次的打标任务
from typing import List, Dict                                          # 类型注解

from src.config import config                                          # 全局配置单例（CLI 引擎、并发数、超时等）
from src.prompts.templates import get_tagging_prompt_batch              # 模板函数：把评论拼成打标 prompt

# 配置日志格式：时间 - 模块名 - 级别 - 消息
logging.basicConfig(
    level=logging.INFO,                                                # 默认 INFO 级别（可改为 DEBUG 看更多细节）
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)                                   # 获取当前模块的 logger 实例


def analyze_all(reviews: List[Dict], batch_size: int = 30) -> List[Dict]:
    """
    使用 Claude Code CLI 并发分析所有评论（Phase 1 的核心函数）

    流程：评论分批 → 提交线程池并发执行 → 收集结果 → 失败重试 → 返回带标签的评论

    Args:
        reviews: 原始评论列表，每条评论需包含:
            - review_id: 12位唯一标识（UUID前12位）
            - body: 评论正文
            - rating: 评分（0.0-5.0）
        batch_size: 每批处理数量，默认30，推荐范围20-50
            - 太小：CLI 调用次数多，overhead 大
            - 太大：单次 prompt 太长，容易超时

    Returns:
        添加了以下字段的评论列表:
            - sentiment: 情感倾向 (强烈推荐/推荐/中立/不推荐/强烈不推荐)
            - info_score: 信息密度评分 (1-20，分越高信息量越大)
            - tags: 22维度标签字典，如 {"人群_性别": "男", "场景_使用场景": "家用"}

    Raises:
        ValueError: 当 batch_size 不在 [20, 50] 范围内时
    """
    # ========== 参数校验 ==========
    if not 20 <= batch_size <= 50:                                     # 批次太小 overhead 太大，太大会超时
        raise ValueError(f"batch_size 必须在 20-50 之间，当前值: {batch_size}")

    if not reviews:                                                     # 空列表直接返回（不打空仗）
        logger.warning("输入评论列表为空")
        return []

    total_reviews = len(reviews)                                       # 总评论数（用于进度计算）
    logger.info(f"开始分析 {total_reviews} 条评论，批次大小: {batch_size}")
    logger.info(f"使用引擎: {config.CLI_ENGINE.upper()} CLI ({config.cli_cmd})")

    # ========== 分批 ==========
    # 把 100 条评论切成 [30, 30, 30, 10] 四批
    batches = _chunk_reviews(reviews, batch_size)                      # 二维列表：[[批1评论], [批2评论], ...]
    total_batches = len(batches)                                        # 总批次数
    logger.info(f"共分为 {total_batches} 个批次")

    # ========== 初始化数据结构 ==========
    results = []                                                        # 成功的结果汇总列表
    failed_batches = []                                                 # 记录哪些批次失败了（存的是批次索引）
    batch_times = {}                                                    # 每批次耗时（key=批次索引, value=秒）
    batch_start_times = {}                                              # 每批次开始时间（key=批次索引, value=time.time()）
    completed_count = 0                                                 # 已完成批次的计数器（按完成顺序，非提交顺序）

    # ========== 进度条（可选） ==========
    # tqdm 不是必须依赖，装了就显示好看的进度条，没装就用文本日志
    try:
        from tqdm import tqdm                                           # 尝试导入 tqdm 进度条库
        progress_bar = tqdm(total=total_reviews, desc="打标进度", unit="条", disable=False)
        logger.info(f"✅ 进度条已创建，总评论数: {total_reviews}")
    except ImportError:                                                 # 没装 tqdm 就降级
        progress_bar = None
        logger.warning("⚠️  未安装 tqdm，将使用文本日志显示进度")

    # 打印启动信息（方便用户确认参数）
    logger.info(f"🚀 启动并发处理: {total_batches}个批次，每批{batch_size}条评论")
    logger.info(f"🔧 并发工作线程数: {config.MAX_CONCURRENT_AGENTS}")
    logger.info(f"⏱️  CLI超时设置: {config.CLI_TIMEOUT}秒/批次")
    logger.info(f"🕐 总体开始时间: {time.strftime('%H:%M:%S')}")

    # ========== 核心：线程池并发执行 ==========
    # ThreadPoolExecutor 维护一个固定大小的线程池
    # max_workers=4 表示最多同时跑 4 个批次，第 5 批等前面的空出来
    with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_AGENTS) as executor:
        # ── 提交所有任务 ──
        future_to_batch = {}                                           # {Future对象: 批次索引}，用于追溯结果
        logger.info(f"📤 提交{total_batches}个批次任务到线程池...")

        for i, batch in enumerate(batches):                            # 遍历所有批次
            batch_start_times[i] = time.time()                          # 记录该批次开始时间
            future = executor.submit(analyze_batch, batch, i)           # 提交任务：analyze_batch(batch, i)
            future_to_batch[future] = i                                 # 建立映射：通过 Future 找到批次索引
            logger.info(f"   ✓ 批次 {i + 1}/{total_batches} 已提交 (包含{len(batch)}条评论)")

        logger.info(f"✅ 所有批次已提交，等待处理结果...")
        logger.info(f"💡 提示: 如果长时间无进度更新，请检查 CLI 是否可用")

        # ── 收集结果（as_completed：谁先完成先处理谁，不按提交顺序） ──
        for future in as_completed(future_to_batch):                   # 迭代已完成的任务（哪个先完就先 yield）
            batch_idx = future_to_batch[future]                         # 从映射中找到是对应哪个批次
            completed_count += 1                                        # 完成计数 +1

            # 计算该批次的耗时
            elapsed = time.time() - batch_start_times[batch_idx]       # 结束时间 - 开始时间

            logger.info(f"⏳ 批次 {batch_idx + 1}/{total_batches} 正在处理...")

            try:
                batch_results = future.result()                         # 获取 analyze_batch 的返回值（可能抛异常）
                results.extend(batch_results)                           # 把打标结果追加到总列表

                # 更新进度条
                if progress_bar:
                    progress_bar.update(len(batch_results))              # 进度条走新完成的数量
                    progress_bar.set_postfix({                          # 设置进度条右侧的额外信息
                        "批次": f"{len(results) // batch_size + 1}/{total_batches}",
                        "已完成": f"{len(results)}/{total_reviews}",
                        "进度": f"{len(results)/total_reviews*100:.1f}%"
                    })
                    progress_bar.refresh()                               # 立即刷新显示

                # 文本日志输出进度
                logger.info(
                    f"✅ 批次 {batch_idx + 1}/{total_batches} 完成 "
                    f"({len(results)}/{total_reviews}, {len(results)/total_reviews*100:.1f}%, "
                    f"耗时: {elapsed:.1f}秒, 完成序列: {completed_count})"
                )

            except Exception as e:                                     # 该批次处理失败
                failed_batches.append(batch_idx)                        # 记下失败批次索引（后面统一重试）
                logger.error(
                    f"❌ 批次 {batch_idx + 1}/{total_batches} 失败: {str(e)}",
                    exc_info=True                                       # 打印完整堆栈
                )

                # 失败批次也要更新进度条（标注失败的那批条数）
                if progress_bar:
                    batch_size_actual = len(batches[batch_idx]) if batch_idx < len(batches) else 0
                    progress_bar.update(batch_size_actual)
                    progress_bar.set_postfix({
                        "批次": f"{len(results) // batch_size + 1}/{total_batches}",
                        "已完成": f"{len(results)}/{total_reviews}",
                        "进度": f"{len(results)/total_reviews*100:.1f}%"
                    })
                    progress_bar.refresh()

    # 关闭进度条（离开 with 块后需要手动 close）
    if progress_bar:
        progress_bar.close()

    # ========== 失败重试 ==========
    # 所有批次都跑完后，对失败的批次再做一次尝试
    if failed_batches:
        logger.warning(f"有 {len(failed_batches)} 个批次失败，尝试重试...")
        retry_results = _retry_failed_batches(
            [batches[i] for i in failed_batches],                       # 取出失败批次的原始数据
            failed_batches                                               # 传入原始索引用于日志
        )
        results.extend(retry_results)                                   # 重试结果也追加进去

    # ========== 最终统计 ==========
    success_count = len(results)                                        # 成功的条数
    failed_count = total_reviews - success_count                        # 失败的条数

    # 计算耗时统计
    total_time = time.time() - batch_start_times[0] if batch_start_times else 0  # 从第一个批次开始到现在的总耗时
    avg_time_per_batch = sum(batch_times.values()) / len(batch_times) if batch_times else 0
    avg_time_per_review = total_time / total_reviews if total_reviews > 0 else 0

    # 输出汇总统计（分隔线让它醒目）
    logger.info("=" * 60)
    logger.info("📊 评论打标完成统计")
    logger.info(f"   总评论数: {total_reviews} 条")
    logger.info(f"   总批次: {total_batches} 批")
    logger.info(f"   总耗时: {total_time/60:.1f}分钟 ({total_time:.0f}秒)")
    logger.info(f"   平均每批: {avg_time_per_batch:.1f}秒")
    logger.info(f"   平均每条: {avg_time_per_review:.1f}秒")
    logger.info(f"   成功: {success_count} 条, 失败: {failed_count} 条")
    logger.info(f"   成功率: {success_count/total_reviews*100:.1f}% ({success_count}/{total_reviews})")
    logger.info("=" * 60)

    return results                                                     # 返回所有带标签的评论


def analyze_batch(batch: List[Dict], batch_idx: int = -1) -> List[Dict]:
    """
    分析单批评论（这是线程池里每个线程实际执行的函数）

    三步流程：
    1. 把评论拼成打标 prompt（调用 get_tagging_prompt_batch）
    2. 用 subprocess 调用 Claude/OpenCode CLI（调用 _call_claude_cli）
    3. 解析 CLI 返回的 JSON 响应（调用 _parse_batch_response）

    内置最多 3 次重试，失败后返回"分析失败"标记的原始评论（不丢数据）

    Args:
        batch: 评论批次列表，20-50 条
        batch_idx: 批次索引（用于日志中显示"A批次 X/Y"）

    Returns:
        打标结果列表
    """
    max_retries = 3                                                    # 最大重试次数（CLI 偶尔会抽风）
    last_error = None                                                  # 记录最后一次错误

    # 获取当前线程名（方便多线程日志区分）
    thread_id = threading.current_thread().name
    batch_display = batch_idx + 1 if batch_idx >= 0 else "?"          # 人类友好的批次编号（从1开始）

    logger.info(f"🔵 批次 {batch_display} 由线程 '{thread_id}' 开始处理 (包含 {len(batch)} 条评论)")
    logger.debug(f"📦 开始处理批次，包含 {len(batch)} 条评论")

    for attempt in range(max_retries):                                 # 最多尝试 max_retries 次
        try:
            # Step 1: 构造提示词
            # 把评论列表 + 标签体系说明拼成一个完整的打标 prompt
            logger.debug(f"🔨 构造提示词 (尝试 {attempt + 1}/{max_retries})...")
            prompt = get_tagging_prompt_batch(batch)                   # 生成：含评论数据 + 标签体系 + JSON 格式要求

            # Step 2: 🔥 调用 CLI（subprocess 启动 Claude Code，传 prompt 进去）
            logger.info(f"📞 调用 Claude Code CLI (尝试 {attempt + 1}/{max_retries})...")
            logger.debug(f"   - 提示词长度: {len(prompt)} 字符")
            logger.debug(f"   - 超时设置: {config.CLI_TIMEOUT} 秒")

            response_text = _call_claude_cli(prompt)                   # 阻塞等待 CLI 返回，超时会抛异常

            logger.info(f"✅ CLI 调用成功，响应长度: {len(response_text)} 字符")

            # Step 3: 解析 JSON 响应
            # CLI 返回的是自然语言包裹的 JSON，需要提取数组 + 解析 + 合并回原评论
            logger.debug(f"🔍 解析 JSON 响应...")
            results = _parse_batch_response(
                response_text,                                          # CLI 返回的原始文本（含 JSON）
                batch                                                    # 原始评论批次（用于 review_id 对账合并）
            )

            logger.info(
                f"✅ 批次分析成功: {len(results)}/{len(batch)} 条 "
                f"(尝试 {attempt + 1}/{max_retries}, 线程: {thread_id})"
            )

            return results                                              # 成功！返回打标结果

        except json.JSONDecodeError as e:                              # CLI 返回的不是合法 JSON
            last_error = e
            logger.warning(
                f"⚠️  JSON 解析失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            # 最后一次尝试也失败了 → 返回"未打标"的原始评论
            if attempt == max_retries - 1:
                logger.error("❌ JSON 解析失败，返回原始评论（未打标）")
                return _get_failed_batch_results(batch, "JSON_PARSE_ERROR")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:  # CLI 超时或进程错误
            last_error = e
            logger.warning(
                f"⚠️  CLI 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            if attempt == max_retries - 1:                             # 重试耗尽
                logger.error("❌ CLI 调用失败，返回原始评论（未打标）")
                return _get_failed_batch_results(batch, str(e))

        except Exception as e:                                          # 其他未知异常
            last_error = e
            logger.warning(
                f"⚠️  未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            if attempt == max_retries - 1:                             # 重试耗尽
                logger.error("❌ 未知错误，返回原始评论（未打标）")
                return _get_failed_batch_results(batch, str(e))

    # 理论上不会执行到这里（每个分支都有 return），但保留作为最后兜底
    return _get_failed_batch_results(batch, str(last_error))


# ==================== 私有辅助函数（以下划线开头，模块内部使用） ====================

def _call_claude_cli(prompt: str, max_retries: int = 3) -> str:
    """
    调用 CLI 引擎进行 AI 推理（核心桥接函数）

    通过 config.build_cli_cmd() 统一构建命令，支持 claude / opencode 双引擎。
    本质就是 subprocess.run(["claude", "--print", "--dangerously-skip-permissions", prompt])

    流程：
    claude → subprocess: claude --print --dangerously-skip-permissions "<prompt>"
    opencode → subprocess: opencode run "<prompt>"

    Args:
        prompt: 完整的打标提示词
        max_retries: 最大重试次数（默认3次）

    Returns:
        str: CLI 返回的 stdout 文本内容（包含 AI 分析结果 JSON）

    Raises:
        subprocess.TimeoutExpired: 超时（默认 600 秒）
        subprocess.SubprocessError: 子进程错误（返回非0或空输出）
    """
    logger.info(f"🔧 使用 {config.CLI_ENGINE.upper()} CLI 引擎")

    for attempt in range(max_retries):
        try:
            # 通过 config 的统一入口构建命令（自动处理引擎差异 + 绝对路径解析）
            cmd = config.build_cli_cmd(prompt)                         # 返回如 ["claude", "--print", "--dangerously-skip-permissions", prompt]

            logger.debug(f"调用 CLI: {cmd[0]} <prompt长度={len(prompt)}>")

            # subprocess.run: 启动子进程，等待它运行完
            result = subprocess.run(
                cmd,                                                     # 命令 + 参数列表
                capture_output=True,                                     # 捕获 stdout 和 stderr（不打印到终端）
                text=True,                                                # 返回字符串而非 bytes
                timeout=config.CLI_TIMEOUT,                              # 超时时间（默认600秒=10分钟）
                check=True,                                               # 返回码非0时自动抛出 CalledProcessError
                env={**os.environ, 'PATH': os.environ.get('PATH', '')}   # 传递当前环境变量（确保子进程能继承 .env 中设置的所有环境变量）
            )

            # 检查返回码（check=True 已经做了，这里是双重保险）
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "未知错误"
                logger.error(f"🔴 CLI 失败 (返回码 {result.returncode})")
                logger.error(f"🔴 错误信息: {error_msg}")
                raise subprocess.SubprocessError(
                    f"CLI 返回非零状态码 ({result.returncode}): {error_msg}"
                )

            # 获取 stdout 内容（AI 的分析结果就在这里）
            response_text = result.stdout.strip()
            logger.debug(f"CLI 返回内容长度: {len(response_text)}")

            if not response_text:                                       # stdout 为空
                raise subprocess.SubprocessError("CLI 返回空内容")

            return response_text                                         # 成功返回

        except subprocess.TimeoutExpired:                               # CLI 执行超时
            timeout_seconds = config.CLI_TIMEOUT
            logger.warning(
                f"⏰ CLI 调用超时 (尝试 {attempt + 1}/{max_retries}, "
                f"等待超过 {timeout_seconds} 秒)"
            )
            # 给出排查建议
            logger.warning(f"💡 可能原因:")
            logger.warning(f"   1. CLI 正在处理复杂任务，需要更长时间")
            logger.warning(f"   2. 网络延迟或 API 响应慢")
            logger.warning(f"   3. CLI 进程卡住或崩溃")
            logger.warning(f"💡 建议:")
            logger.warning(f"   - 检查 CLI 是否可用: {config.cli_cmd} --version")
            logger.warning(f"   - 增加超时时间: 修改 config.CLI_TIMEOUT")
            logger.warning(f"   - 减少批次大小: 降低单批次评论数")
            if attempt == max_retries - 1:                              # 最后一次重试也超时，抛出异常
                raise

        except subprocess.CalledProcessError as e:                     # CLI 返回非0状态码
            logger.warning(f"❌ CLI 调用失败 (尝试 {attempt + 1}/{max_retries}): {e.stderr}")
            if attempt == max_retries - 1:
                raise subprocess.SubprocessError(f"CLI 执行失败: {e.stderr}")

        except Exception as e:                                          # 其他意外错误
            logger.warning(f"⚠️  未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise

    raise RuntimeError("CLI 调用失败：超过最大重试次数")                 # 兜底：理论上不会到这儿


def _chunk_reviews(reviews: List[Dict], batch_size: int) -> List[List[Dict]]:
    """
    将评论列表按批次大小切成多组（纯切片，不涉及任何 AI 调用）

    例如: [1,2,3,4,5,6,7,8,9,10] batch_size=3
    返回: [[1,2,3], [4,5,6], [7,8,9], [10]]

    Args:
        reviews: 完整评论列表
        batch_size: 每组大小

    Returns:
        二维列表
    """
    batches = []
    for i in range(0, len(reviews), batch_size):                       # 从0开始，每次跳 batch_size
        batches.append(reviews[i:i + batch_size])                       # 切片：取 [i, i+batch_size) 区间
    return batches


def _parse_batch_response(
    response_text: str,
    original_batch: List[Dict]
) -> List[Dict]:
    """
    解析 CLI 返回的响应文本 → 提取 JSON 数组 → 合并回原始评论

    CLI 返回的文本通常是这样的：
    ```
    好的，这是分析结果：
    ```json
    [{"review_id": "xxx", "sentiment": "强烈推荐", "tags": {...}}, ...]
    ```
    ```

    所以需要：清理 markdown 标记 → 找到 JSON 数组 → 解析 → 按 review_id 合并

    Args:
        response_text: CLI 返回的原始文本（可能含 markdown 包裹）
        original_batch: 原始评论批次（用于根据 review_id 合并数据）

    Returns:
        合并后的打标评论列表

    Raises:
        json.JSONDecodeError: JSON 完全无法解析时
        ValueError: 响应格式不正确时
    """
    # ── Step 1: 清理响应文本（去掉 markdown 代码块标记） ──
    cleaned_text = response_text.strip()

    # 去掉开头的 ```json 或 ```JSON
    if cleaned_text.startswith("```json"):                              # 匹配 ```json
        cleaned_text = cleaned_text[7:]                                  # 截掉前7个字符
    elif cleaned_text.startswith("```JSON"):                            # 匹配 ```JSON（大写）
        cleaned_text = cleaned_text[7:]
    if cleaned_text.startswith("```"):                                  # 匹配纯 ```
        cleaned_text = cleaned_text[3:]                                  # 截掉前3个字符
    if cleaned_text.endswith("```"):                                    # 去掉结尾的 ```
        cleaned_text = cleaned_text[:-3]
    cleaned_text = cleaned_text.strip()

    # ── Step 2: 找到 JSON 数组的起止位置 ──
    # 用括号匹配而非简单切片，因为评论正文里也可能有 [] 字符
    start_idx = cleaned_text.find('[')                                  # 找第一个 [
    if start_idx == -1:                                                 # 没找到 JSON 数组
        raise ValueError("响应中未找到 JSON 数组起始符号 '['")

    # 用计数器匹配成对的方括号（处理嵌套情况）
    bracket_count = 0                                                    # 括号深度计数器
    end_idx = -1
    for i in range(start_idx, len(cleaned_text)):
        if cleaned_text[i] == '[':
            bracket_count += 1                                           # 遇到 [ 深度+1
        elif cleaned_text[i] == ']':
            bracket_count -= 1                                           # 遇到 ] 深度-1
            if bracket_count == 0:                                       # 深度归零 = 找到了配对的 ]
                end_idx = i + 1                                          # +1 是因为切片是左闭右开
                break

    if end_idx == -1:                                                    # JSON 被截断（CLI 输出不完整）
        logger.warning("JSON 响应可能被截断，尝试修复...")
        # 尝试取到最后一个完整的 } 对象，手动补 ]
        last_complete_obj = cleaned_text.rfind('}')                     # 找最后一个 }
        if last_complete_obj > start_idx:
            cleaned_text = cleaned_text[start_idx:last_complete_obj + 1] + ']'  # 补一个 ]
        else:
            raise ValueError("无法修复截断的 JSON 响应")
    else:
        cleaned_text = cleaned_text[start_idx:end_idx]                   # 正常：截取 [ 到 ] 之间的内容

    # ── Step 3: 解析 JSON ──
    try:
        results = json.loads(cleaned_text)                               # JSON 字符串 → Python 列表
    except json.JSONDecodeError as e:                                    # 实在解析不了了
        logger.error(f"JSON 解析失败。响应内容: {cleaned_text[:500]}...")  # 打印前500字符帮助诊断
        logger.error(f"完整响应: {response_text[:1000]}...")            # 打印完整响应的前1000字符
        raise

    # ── Step 4: 验证响应格式 ──
    if not isinstance(results, list):                                    # CLI 返回的不是数组（格式错误）
        raise ValueError(f"响应应为数组格式，实际: {type(results)}")

    # ── Step 5: 按 review_id 合并打标结果到原始评论 ──
    original_map = {r["review_id"]: r for r in original_batch}          # 构建 {review_id: 原始评论} 字典

    merged_results = []
    for result in results:                                               # 遍历 AI 返回的每条结果
        review_id = result.get("review_id")                              # 取 AI 返回的 review_id

        if not review_id:                                                # 结果里没有 review_id
            logger.warning("响应中缺少 review_id，跳过")
            continue

        if review_id not in original_map:                                # 结果里的 ID 在原始批次里找不到
            logger.warning(f"未找到对应的原始评论: {review_id}")
            continue

        # 合并原始数据和打标结果（原始数据如 body/rating 保留，AI 加的 sentiment/tags 补进去）
        merged = {**original_map[review_id], **result}                  # 字典解包合并，result 的字段会覆盖同名原始字段
        merged_results.append(merged)

    # ── Step 6: 检查遗漏（AI 可能漏掉了一些评论没返回） ──
    if len(merged_results) < len(original_batch):                       # 部分评论没被 AI 处理
        missing_count = len(original_batch) - len(merged_results)
        logger.warning(f"有 {missing_count} 条评论未被正确处理，返回原始数据")

        # 补充未处理的评论（标记为"解析失败"）
        processed_ids = {r["review_id"] for r in merged_results}        # 已处理的 review_id 集合
        for original in original_batch:
            if original["review_id"] not in processed_ids:              # 这条在 AI 返回里找不到
                merged_results.append({
                    **original,                                           # 保留原始数据
                    "sentiment": "解析失败",                              # 标记失败
                    "info_score": 0,                                      # 信息评分为 0
                    "tags": {}                                            # 标签为空
                })

    return merged_results


def _get_failed_batch_results(
    batch: List[Dict],
    error_message: str
) -> List[Dict]:
    """
    为处理失败的批次生成兜底结果（确保不丢数据）

    这批评论不会被打标，但会被保留并标记错误原因，
    后续流程可以正常进行，只是这批数据没有标签。

    Args:
        batch: 原始评论批次
        error_message: 失败原因（JSON_PARSE_ERROR / RETRY_FAILED 等）

    Returns:
        带错误标记的评论列表
    """
    results = []
    for review in batch:
        results.append({
            **review,                                                    # 保留原始字段
            "sentiment": "分析失败",                                     # 标记为失败
            "info_score": 0,                                              # 无评分
            "tags": {},                                                   # 无标签
            "_error": error_message                                       # 私藏字段：记录失败原因（方便排查）
        })
    return results


def _retry_failed_batches(
    failed_batches: List[List[Dict]],
    failed_indices: List[int]
) -> List[Dict]:
    """
    重试失败的批次（在主线程中串行执行，不做并发）

    之所以串行重试而非并发：
    1. 失败批次通常很少（< 总数的10%）
    2. 避免重试又全部失败浪费资源
    3. 串行更方便日志追踪

    Args:
        failed_batches: 失败的批次数据列表
        failed_indices: 失败批次的原始索引（用于日志输出）

    Returns:
        重试后的评论列表（成功的带标签，仍然失败的标记 error）
    """
    results = []

    for batch, idx in zip(failed_batches, failed_indices):               # 逐个处理失败批次
        try:
            logger.info(f"重试批次 {idx + 1}")
            batch_results = analyze_batch(batch)                          # 再跑一次（不带重试参数的 analyze_batch 内部还有3次重试）
            results.extend(batch_results)
            logger.info(f"批次 {idx + 1} 重试成功")
        except Exception as e:                                            # 重试也失败了...
            logger.error(f"批次 {idx + 1} 重试仍然失败: {str(e)}")
            # 返回未打标的原始评论（不丢数据，只是这批没标签）
            results.extend(_get_failed_batch_results(batch, f"RETRY_FAILED: {str(e)}"))

    return results


# ==================== 便捷函数（对外暴露的工具函数） ====================

def analyze_single(review: Dict) -> Dict:
    """
    分析单条评论（便捷封装）
    内部实际上还是走 analyze_batch，只是把单条评论包装成只有1个元素的批次。

    适用场景：想快速看某一条评论的打标结果，不想跑整个流程

    Args:
        review: 单条评论，需包含 review_id, body, rating

    Returns:
        添加了 sentiment, info_score, tags 的评论
    """
    results = analyze_batch([review])                                    # 包装成单元素列表，调用 analyze_batch
    return results[0] if results else review                             # 取第一条结果


def get_analysis_stats(results: List[Dict]) -> Dict:
    """
    获取分析统计信息（用于了解打标质量）
    统计多少个成功、多少个失败、情感分布、平均信息密度

    Args:
        results: analyze_all 返回的结果列表

    Returns:
        统计信息字典:
            - total: 总评论数
            - success: 成功打标数
            - failed: 失败数
            - sentiment_distribution: {情感标签: 数量}
            - avg_info_score: 平均信息密度（1-20）
    """
    total = len(results)

    if total == 0:                                                       # 空结果
        return {
            "total": 0, "success": 0, "failed": 0,
            "sentiment_distribution": {}, "avg_info_score": 0
        }

    # 统计失败数（sentiment 为"分析失败"或"解析失败"的）
    failed = sum(1 for r in results if r.get("sentiment") in ["分析失败", "解析失败"])
    success = total - failed

    # 统计情感分布（如 "强烈推荐": 45, "中立": 12, ...）
    sentiment_dist = {}
    for r in results:
        s = r.get("sentiment", "未知")
        sentiment_dist[s] = sentiment_dist.get(s, 0) + 1                # dict.get(key, default) 简便计数

    # 平均信息密度（只取成功打标的，排除 info_score=0 的失败数据）
    valid_scores = [r.get("info_score", 0) for r in results if r.get("info_score", 0) > 0]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "sentiment_distribution": sentiment_dist,
        "avg_info_score": round(avg_score, 2)                            # 保留2位小数
    }


if __name__ == "__main__":                                               # 直接运行此文件时的测试代码
    # 两条测试评论（不会真正调 CLI，只是展示数据结构）
    test_reviews = [
        {
            "review_id": "test_001",
            "body": "Amazing product! I bought this for my husband and he loves it. Great quality and fast shipping.",
            "rating": 5
        },
        {
            "review_id": "test_002",
            "body": "It's okay, does what it's supposed to do.",
            "rating": 3
        }
    ]

    print("测试 analyze_single:")
    result = analyze_single(test_reviews[0])
    print(f"Sentiment: {result.get('sentiment')}")
    print(f"Info Score: {result.get('info_score')}")
    print(f"Tags: {list(result.get('tags', {}).keys())}")
