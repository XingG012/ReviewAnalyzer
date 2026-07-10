"""
SQLite 任务持久化 — 分析任务历史存储与查询
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "tasks.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据库表"""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          TEXT PRIMARY KEY,
                asin        TEXT NOT NULL DEFAULT 'UNKNOWN',
                status      TEXT NOT NULL DEFAULT 'running',
                output_dir  TEXT DEFAULT '',
                error_msg   TEXT DEFAULT '',
                total_reviews INTEGER DEFAULT 0,
                persona_count INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL,
                completed_at TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                id            TEXT PRIMARY KEY,
                original_name TEXT NOT NULL,
                stored_path   TEXT NOT NULL,
                size_bytes    INTEGER DEFAULT 0,
                review_count  INTEGER DEFAULT 0,
                source        TEXT DEFAULT 'csv',
                created_at    TEXT NOT NULL
            )
        """)
        conn.commit()


def save_task(
    task_id: str = "",
    asin: str = "UNKNOWN",
    status: str = "running",
    output_dir: str = "",
    error_msg: str = "",
    total_reviews: int = 0,
    persona_count: int = 0,
) -> str:
    """创建或更新任务记录，返回 task_id"""
    if not task_id:
        task_id = uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc).isoformat()
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO tasks (id, asin, status, output_dir, error_msg,
                   total_reviews, persona_count, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (task_id, asin, status, output_dir, error_msg,
                 total_reviews, persona_count, created_at),
            )
            conn.commit()
    else:
        completed_at = ""
        if status in ("done", "failed"):
            completed_at = datetime.now(timezone.utc).isoformat()
        with _get_conn() as conn:
            conn.execute(
                """UPDATE tasks SET status=?, output_dir=?, error_msg=?,
                   total_reviews=?, persona_count=?, completed_at=?
                   WHERE id=?""",
                (status, output_dir, error_msg, total_reviews, persona_count,
                 completed_at, task_id),
            )
            conn.commit()
    return task_id


def list_tasks(limit: int = 50) -> List[Dict]:
    """查询历史任务列表（按创建时间倒序）"""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_task(task_id: str) -> Optional[Dict]:
    """按 ID 获取单条任务"""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
    return dict(row) if row else None


# ── 上传文件管理 ───────────────────────────────────────────

def save_upload(
    original_name: str,
    stored_path: str,
    size_bytes: int = 0,
    review_count: int = 0,
    source: str = "csv",
) -> str:
    """保存上传文件记录，返回 upload_id"""
    upload_id = uuid.uuid4().hex[:12]
    created_at = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO uploads (id, original_name, stored_path, size_bytes,
               review_count, source, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (upload_id, original_name, stored_path, size_bytes,
             review_count, source, created_at),
        )
        conn.commit()
    return upload_id


def list_uploads(limit: int = 20) -> List[Dict]:
    """查询已上传文件列表（按时间倒序）"""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM uploads ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_upload(upload_id: str) -> Optional[Dict]:
    """按 ID 获取上传文件记录"""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM uploads WHERE id=?", (upload_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_upload(upload_id: str) -> bool:
    """删除上传记录（同时删除磁盘文件）"""
    info = get_upload(upload_id)
    if not info:
        return False
    # 删除磁盘文件
    sp = info.get("stored_path", "")
    if sp and Path(sp).exists():
        Path(sp).unlink()
    # 删除数据库记录
    with _get_conn() as conn:
        conn.execute("DELETE FROM uploads WHERE id=?", (upload_id,))
        conn.commit()
    return True


# 首次 import 时初始化
init_db()
