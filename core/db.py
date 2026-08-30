"""数据库连接与建表：默认 SQLite，检测到 DATABASE_URL 时切换 PostgreSQL。"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
DB_PATH = DATA_DIR / "guatfood.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS user (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL UNIQUE,
    password   TEXT NOT NULL,
    nickname   TEXT,
    avatar     TEXT,
    role       TEXT NOT NULL DEFAULT 'USER',
    status     TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS canteen (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    location   TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS food_window (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    canteen_id   INTEGER NOT NULL,
    submitter_id INTEGER,
    name         TEXT NOT NULL,
    description  TEXT,
    cover_image  TEXT,
    location     TEXT,
    status       TEXT NOT NULL DEFAULT 'PUBLISHED',
    view_count   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_window_canteen ON food_window (canteen_id);

CREATE TABLE IF NOT EXISTS dish (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id    INTEGER NOT NULL,
    submitter_id INTEGER,
    name         TEXT NOT NULL,
    description  TEXT,
    image        TEXT,
    price        REAL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'PUBLISHED',
    view_count   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_dish_window ON dish (window_id);

CREATE TABLE IF NOT EXISTS rating (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id   INTEGER NOT NULL,
    taste       INTEGER NOT NULL DEFAULT 3,
    value_score INTEGER NOT NULL DEFAULT 3,
    portion     INTEGER NOT NULL DEFAULT 3,
    comment     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (user_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_rating_target ON rating (target_type, target_id);

CREATE TABLE IF NOT EXISTS like_record (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id   INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (user_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_like_target ON like_record (target_type, target_id);

CREATE TABLE IF NOT EXISTS favorite (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id   INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (user_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_fav_target ON favorite (target_type, target_id);
"""

_pool = None


def _is_pg() -> bool:
    """是否使用 PostgreSQL：以环境变量 DATABASE_URL 是否存在为准（惰性读取）。"""
    return bool(os.environ.get("DATABASE_URL"))


def _norm(d: dict) -> dict:
    """PG 的 AVG() 返回 Decimal（SQLite 返回 float），统一转 float 保持两端一致。"""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in d.items()}


def _quote_user(sql: str) -> str:
    """`user` 是 PostgreSQL 保留字，表名需加双引号；词边界匹配避免误伤 user_id/username。"""
    return re.sub(r"\buser\b", '"user"', sql)


def _adapt_sql(sql: str) -> str:
    """把 SQLite 方言翻译成 PostgreSQL（仅 PG 后端调用）。"""
    sql = sql.replace(
        "datetime('now', 'localtime', '-30 days')",
        "CURRENT_TIMESTAMP - INTERVAL '30 days'",
    )
    sql = sql.replace("datetime('now', 'localtime')", "CURRENT_TIMESTAMP")
    sql = sql.replace("?", "%s")
    sql = sql.replace(" LIKE ", " ILIKE ")
    sql = _quote_user(sql)
    return sql


def _pg_schema() -> str:
    """由 SQLite SCHEMA 转换出 PostgreSQL 版（避免两套 schema 漂移）。"""
    sql = SCHEMA
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    # 各表 created_at/updated_at 列对齐空格数不一（1~3 个），用 \s+ 匹配
    sql = re.sub(
        r"created_at\s+TEXT NOT NULL DEFAULT \(datetime\('now', 'localtime'\)\)",
        "created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        sql,
    )
    sql = re.sub(
        r"updated_at\s+TEXT NOT NULL DEFAULT \(datetime\('now', 'localtime'\)\)",
        "updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        sql,
    )
    sql = sql.replace("REAL DEFAULT 0", "DOUBLE PRECISION DEFAULT 0")
    sql = _quote_user(sql)
    return sql


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


def _get_pool():
    """惰性创建并复用 psycopg 连接池。"""
    global _pool
    if _pool is None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            os.environ["DATABASE_URL"],
            min_size=1,
            max_size=4,
            kwargs={"row_factory": dict_row},
        )
    return _pool


@contextmanager
def get_conn():
    """提供连接上下文：SQLite 提交并关闭；PG 由连接池管理提交/回滚。"""
    if _is_pg():
        with _get_pool().connection() as conn:
            yield conn
        return
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    if _is_pg():
        schema = _pg_schema()
        with get_conn() as conn:
            for stmt in schema.split(";"):
                if stmt.strip():
                    conn.execute(stmt)
        return
    ensure_dirs()
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def query(sql: str, params: tuple = ()) -> list[dict]:
    pg = _is_pg()
    if pg:
        sql = _adapt_sql(sql)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_norm(dict(r)) for r in rows] if pg else [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    pg = _is_pg()
    if pg:
        sql = _adapt_sql(sql)
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return _norm(dict(row)) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """执行写操作；SQLite 返回 lastrowid，PG 对 INSERT 返回 RETURNING id。"""
    if _is_pg():
        sql = _adapt_sql(sql)
        with get_conn() as conn:
            if sql.lstrip().upper().startswith("INSERT"):
                row = conn.execute(sql.rstrip().rstrip(";") + " RETURNING id", params).fetchone()
                return row["id"] if row else None
            conn.execute(sql, params)
            return None
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def execute_many(sql: str, seq: list[tuple]) -> None:
    if _is_pg():
        sql = _adapt_sql(sql)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, seq)
        return
    with get_conn() as conn:
        conn.executemany(sql, seq)
