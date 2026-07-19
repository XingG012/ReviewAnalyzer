"""数据库初始化 — 执行 Alembic 迁移到最新版本"""

import sys
from pathlib import Path

from alembic.config import Config

from alembic import command


def init_db() -> None:
    """执行数据库迁移到最新版本

    在 FastAPI startup 事件中调用，确保每次启动时数据库 schema 是最新的。
    """
    # backend/ 目录（alembic.ini 和 app/ 所在的根目录）
    backend_dir = Path(__file__).resolve().parent.parent.parent

    # 确保 backend/ 在 sys.path 中，这样 alembic/env.py 能 import app.core.config
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # 构造 Alembic 配置
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    # 执行迁移
    command.upgrade(alembic_cfg, "head")
    print("✓ 数据库迁移完成（alembic upgrade head）")


if __name__ == "__main__":
    init_db()
