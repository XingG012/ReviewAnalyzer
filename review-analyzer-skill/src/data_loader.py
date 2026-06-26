import os                                                              # 操作系统接口：检查文件是否存在
import uuid                                                            # 生成唯一 ID：给每条评论分配唯一标识
import tempfile                                                        # 创建临时文件：下载 URL 时用
import urllib.request                                                  # HTTP 请求：从 URL 下载文件
import urllib.parse                                                    # URL 解析：提取文件扩展名
import urllib.error                                                    # URL 错误类型：下载失败时精确捕获异常
import atexit                                                          # 程序退出时自动清理临时文件
import pandas as pd                                                    # 数据分析库：读写 CSV/Excel
from pathlib import Path                                               # 面向对象的文件路径处理
from typing import List, Dict, Tuple                                   # 类型注解：函数签名更清晰


def download_if_url(input_path: str) -> str:
    """
    如果 input_path 是 HTTP/HTTPS URL，则下载到临时文件并返回本地路径；
    如果已经是本地路径，原样返回不做任何处理。

    采用流式写入（边下载边写磁盘）避免大文件撑爆内存，
    使用 atexit 注册清理函数，进程退出时自动删除临时文件。

    Args:
        input_path: 本地文件路径 或 HTTP/HTTPS URL

    Returns:
        str: 本地文件路径（URL 会被下载为临时文件后返回路径）

    Raises:
        ValueError: 当 URL 不可访问、文件过大(>100MB) 或下载失败时
    """
    # 如果不是 http/https 开头 → 就是本地路径 → 原样返回
    if not (input_path.startswith("http://") or input_path.startswith("https://")):
        return input_path

    # 从 URL 中提取文件扩展名，如 https://xxx.com/data.csv → .csv
    parsed = urllib.parse.urlparse(input_path)                         # 解析 URL：scheme、host、path 等
    ext = Path(parsed.path).suffix.lower()                              # 取 path 部分的扩展名（含点），如 .csv
    if ext not in (".csv", ".xls", ".xlsx"):                           # 如果不是表格格式，默认当成 CSV
        ext = ".csv"

    print(f"🌐 检测到 URL，正在下载: {input_path}")

    # 创建临时文件（mkstemp 创建并返回文件描述符 + 文件路径）
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix="review_")  # 文件名如 review_abc123.csv
    os.close(tmp_fd)                                                    # 关闭文件描述符，我们只需要路径，之后用 open 写入

    # 注册清理函数：进程退出时（无论正常/异常）自动删除这个临时文件
    atexit.register(os.unlink, tmp_path)

    # 下载文件
    try:
        # 构造 HTTP 请求（伪装成浏览器，避免被拒）
        req = urllib.request.Request(input_path, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=60) as resp:          # 发 GET 请求，最多等 60 秒
            # 检查文件大小（从响应头 Content-Length 获取），超过 100MB 拒绝
            content_length = resp.headers.get("Content-Length")         # 可能为 None（服务器没返回）
            if content_length and int(content_length) > 100 * 1024 * 1024:  # 100MB = 100*1024*1024 字节
                os.unlink(tmp_path)                                     # 删除已创建的临时文件
                raise ValueError(
                    f"文件过大（{int(content_length) / 1024 / 1024:.1f}MB），"
                    f"超过 100MB 上限限制"
                )

            # 流式写入：从响应读一块写一块，避免整个文件加载到内存
            with open(tmp_path, "wb") as f:                             # 二进制写入模式打开临时文件
                import shutil as _shutil
                _shutil.copyfileobj(resp, f)                            # 把响应流逐块拷贝到文件

        file_size = os.path.getsize(tmp_path)                           # 下载完成后获取实际文件大小
        print(f"✅ 下载完成，文件大小: {file_size / 1024:.1f}KB")
        return tmp_path                                                 # 返回临时文件的本地路径

    except urllib.error.HTTPError as e:                                # HTTP 状态码错误（404/403/500 等）
        os.unlink(tmp_path)                                             # 清理临时文件
        raise ValueError(
            f"下载失败 - HTTP {e.code} {e.reason}: {input_path}\n"
            f"请检查 URL 是否正确，或目标服务器是否可访问"
        )
    except urllib.error.URLError as e:                                 # 网络层错误（DNS/连接超时等）
        if os.path.exists(tmp_path):                                    # 可能已创建但没写完
            os.unlink(tmp_path)
        raise ValueError(
            f"下载失败 - 网络错误: {e.reason}\n"
            f"请检查网络连接和 URL 是否正确"
        )
    except Exception as e:                                              # 其他未知异常也做清理
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise ValueError(f"下载失败: {str(e)}")


def load_reviews_from_file(file_path: str) -> Tuple[List[Dict], pd.DataFrame]:
    """
    智能读取本地 CSV/Excel 文件，模糊匹配列名，清洗无效数据。

    核心功能：
    1. 自动识别编码（UTF-8 → UTF-8-BOM → GBK 逐级回退）
    2. 模糊匹配列名（支持中文/英文列名，如"商品评价正文"、"body"均能识别）
    3. 清洗无效数据（空评论、过短评论、NaN）

    Returns:
        Tuple[List[Dict], pd.DataFrame]:
            - reviews: 清洗后的评论列表，每条包含 review_id、body、rating、date、_original_data
            - original_df: pandas 原始 DataFrame（保留所有列，供后续保存用）
    """
    # 文件存在性检查
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")

    # 根据扩展名选择读取方式，自动尝试多种编码
    if file_path.endswith('.csv'):                                     # CSV 文件
        try:
            df = pd.read_csv(file_path, encoding='utf-8')              # 优先用 UTF-8 读
        except UnicodeDecodeError:                                     # UTF-8 解码失败
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')      # 回退：Windows 带 BOM 的 UTF-8
            except UnicodeDecodeError:                                 # 还是失败
                df = pd.read_csv(file_path, encoding='gbk')            # 最后回退：中文 Windows 常用 GBK
    elif file_path.endswith(('.xls', '.xlsx')):                       # Excel 文件（.xls 或 .xlsx）
        df = pd.read_excel(file_path)                                   # pandas 自动识别 Excel 格式
    else:
        raise ValueError("仅支持 .csv, .xls, .xlsx 格式文件！")

    # 计算物理行数（用于对账说明）
    # 原因：CSV 评论正文可能包含换行符，导致物理行数 > 数据行数
    # 用户可能用 wc -l 数过文件行数，这里提前告诉他差异
    physical_lines = 0                                                 # 物理行数（磁盘上文件的实际行数）
    if file_path.endswith('.csv'):                                     # 只对 CSV 做物理行数统计
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:  # errors='ignore'：遇到无法解码的字符跳过
                physical_lines = sum(1 for _ in f)                      # 遍历每一行并计数（不开额外列表，省内存）
        except Exception:                                               # 统计失败也不影响主流程
            physical_lines = len(df) + 1                                # 降级：用 DataFrame 行数 + 表头估算
    else:                                                               # Excel 文件不存在"物理行"概念
        physical_lines = len(df) + 1                                    # 直接 = 数据行数 + 表头

    # 输出加载信息：实际数据行数 vs 物理行数
    print(f"📄 成功加载表格：检测到 {len(df)} 条有效评论记录 (分布在 {physical_lines} 个物理行中)")
    if physical_lines > len(df) + 1:                                   # 物理行数明显多于（数据行+表头）= 有换行符
        print(f"   💡 提示: 检测到评论正文内含有换行符，系统已自动合并处理。")

    # 定义列名关键词（用于模糊匹配）
    # 不管 CSV 表头叫"内容""评价""review""body"，都能识别
    body_keywords = ['内容', '评价', '正文', 'review', 'body', 'text', 'content']    # 评论正文列
    rating_keywords = ['星级', '打分', '评分', 'rating', 'star', 'score']             # 评分列
    date_keywords = ['时间', '日期', 'date', 'time']                                  # 时间列

    # 模糊列名嗅探函数：遍历 DataFrame 所有列名，找到第一个包含关键词的列
    def find_column(keywords):
        """在 df 的列名中搜索包含任意关键词的列，返回第一个匹配的列名"""
        for col in df.columns:                                         # 遍历所有列名
            col_lower = str(col).lower()                                # 转小写（兼容英文大小写）
            if any(kw in col_lower for kw in keywords):                 # 任一关键词出现在列名中 → 命中
                return col                                              # 返回原始列名（保持大小写）
        return None                                                     # 找不到返回 None

    # 执行列名匹配
    body_col = find_column(body_keywords)                              # 找到评论正文列（必须）
    if not body_col:                                                    # 找不到评论正文列 → 无法继续
        raise Exception(f"❌ 解析失败：表头中找不到包含以下关键词的评论主体列: {body_keywords}")

    rating_col = find_column(rating_keywords)                          # 找到评分列（可选，找不到为 None）
    date_col = find_column(date_keywords)                              # 找到时间列（可选，找不到为 None）

    print(f"🔍 字段映射成功 -> 内容列: '{body_col}' | 评分列: '{rating_col or '未找到'}' | 时间列: '{date_col or '未找到'}")

    # 逐行清洗并构建标准化的评论对象
    reviews = []                                                       # 最终返回的评论列表
    dropped_count = 0                                                  # 被丢弃的无效数据计数

    for idx, row in df.iterrows():                                     # 遍历 DataFrame 每一行
        body_text = str(row[body_col]).strip()                          # 取评论正文，去首尾空白

        # 数据清洗：跳过空值和过短评论
        # pd.isna() 检查是否 NaN；'nan' 字符串也是无效数据；少于 3 个字的评论无分析价值
        if pd.isna(row[body_col]) or body_text.lower() == 'nan' or len(body_text) < 3:
            dropped_count += 1                                          # 累计无效计数
            continue                                                    # 跳过这一行

        # 解析评分：尝试转浮点数，失败则默认为 0
        try:
            rating_val = float(row[rating_col]) if rating_col and pd.notna(row[rating_col]) else 0.0
        except (ValueError, TypeError):                                # 评分列的值无法转数字（如"五星好评"）
            rating_val = 0.0                                            # 默认为 0（未评分）

        # 解析时间：有则转字符串，无则空字符串
        date_val = str(row[date_col]) if date_col and pd.notna(row[date_col]) else ""

        # 构建标准化评论对象
        # _original_data 保留了 CSV 的所有原始列（后续保存 CSV 时会用到）
        # review_id 是 UUID 前 12 位（唯一标识，够用且不冗长）
        review_item = {
            "_original_data": dict(row),                               # 保存原始行数据的完整副本（pandas Series → dict）
            "review_id": str(uuid.uuid4())[:12],                       # 生成 12 位唯一 ID
            "body": body_text,                                          # 评论正文
            "rating": rating_val,                                       # 评分（0.0-5.0）
            "date": date_val                                            # 日期字符串
        }
        reviews.append(review_item)                                    # 加入有效评论列表

    # 输出清洗结果
    print(f"🧹 清洗完毕 -> 有效提取: {len(reviews)} 条记录 (跳过无效/过短评论: {dropped_count} 条)")
    print(f"📊 原始列保留: {list(df.columns)}")                         # 列出 CSV 的所有原始列名

    return reviews, df                                                 # 返回：评论列表 + 原始 DataFrame


if __name__ == "__main__":                                             # 仅直接运行此脚本时执行（`import` 时不执行）
    # 内置冒烟测试：用一段假数据验证加载逻辑是否正常
    dummy_csv = "data/dummy_test.csv"                                  # 测试文件路径
    os.makedirs("data", exist_ok=True)                                 # 确保 data 目录存在
    with open(dummy_csv, "w", encoding="utf-8") as f:                  # 写入测试数据
        f.write("顾客名称,商品评价正文,商品星级,时间记录\n")             # 表头
        f.write("张三,这个键盘手感太棒了！物流也快,5,2026-03-01\n")     # 正常数据
        f.write("李四,质量差，按键不回弹,1,2026-03-02\n")               # 正常数据
        f.write("王五,,5,\n")                                          # 该行应被清洗：评论为空
        f.write("赵六,好,,2026-03-03\n")                               # 该行应被清洗：评论 < 3 字
        f.write("A1,Not bad for the price.,4,2026-03-01\n")           # 英文评论正常数据

    print(f"==== 开始执行 data_loader.py 冒烟测试 ====")
    res = load_reviews_from_file(dummy_csv)                            # 执行加载函数，返回 (reviews列表, df)
    print("\n==== 抽样第一条有效数据 ====")
    import json
    if res:
        print(json.dumps(res[0], indent=2, ensure_ascii=False))       # 格式化打印第一条评论
