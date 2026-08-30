"""一次性迁移脚本：把本地 SQLite（data/guatfood.db）复制到托管 PostgreSQL（如 Supabase）。

用法：
    py migrate_to_pg.py
    py migrate_to_pg.py "postgresql://user:pass@host:5432/dbname"
    py migrate_to_pg.py --yes    # 目标库已有数据时强制清空重导

DATABASE_URL 优先取命令行参数，其次环境变量，再次 .streamlit/secrets.toml。
运行前请先在目标库建好 schema（脚本会自动 db.init_db() 建表）。

安全提示：连接串含密码，请勿提交到仓库；脚本本身不打印连接串明文。
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# 按外键依赖顺序复制（子表在后，其实当前 schema 无外键，但顺序保持清晰）
TABLES = ["user", "canteen", "food_window", "dish", "rating", "like_record", "favorite"]


def _resolve_url(args: list[str]) -> str | None:
    for a in args:
        if not a.startswith("--"):
            return a
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    secrets_path = ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        import tomllib

        try:
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
            if data.get("DATABASE_URL"):
                return str(data["DATABASE_URL"])
        except Exception:
            pass
    return None


def main() -> None:
    args = [a for a in sys.argv[1:]]
    force = "--yes" in args
    url = _resolve_url(args)
    if not url:
        print(
            "未找到 DATABASE_URL：请作为参数传入，"
            "或写入 .streamlit/secrets.toml / 环境变量 DATABASE_URL。"
        )
        sys.exit(1)

    # 必须在 import core.db 之前注入，触发 PostgreSQL 后端
    os.environ["DATABASE_URL"] = url
    from core import db

    sqlite_path = db.DB_PATH
    if not sqlite_path.exists():
        print(f"本地 SQLite 不存在：{sqlite_path}")
        sys.exit(1)

    print("初始化目标库 schema ...")
    db.init_db()

    # 目标库已有数据时需显式 --yes 才清空重导，避免误覆盖
    existing = db.query_one("SELECT COUNT(*) AS c FROM canteen")
    if existing and existing["c"] and not force:
        print(f"目标库已有 {existing['c']} 个食堂（说明已初始化过）。确认清空重导请加 --yes。")
        sys.exit(1)

    # 清空目标表（含序列），保证脚本可重复执行
    for t in reversed(TABLES):
        db.execute(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE")

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    for table in TABLES:
        cols = [c[1] for c in src.execute(f"PRAGMA table_info({table})").fetchall()]
        rows = src.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        for row in rows:
            db.execute(sql, tuple(row[c] for c in cols))
        max_id = src.execute(f"SELECT MAX(id) FROM {table}").fetchone()[0]
        if max_id:
            # SERIAL 序列名固定为 <table>_id_seq；显式带 id 插入不会推进序列，故手动 setval。
            db.execute(f"SELECT setval('{table}_id_seq', {max_id}, true)")
        print(f"  {table}: {len(rows)} 行")

    src.close()
    print("迁移完成。云端 seed_if_empty() 会因已有 canteen 而跳过种子，直接使用迁移数据。")


if __name__ == "__main__":
    main()
