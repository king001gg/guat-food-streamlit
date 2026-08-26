"""数据库连接与建表（SQLite，标准库 sqlite3）。"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
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


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


@contextmanager
def get_conn() -> sqlite3.Connection:
    """提供一个已提交并关闭的连接。"""
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    ensure_dirs()
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """执行写操作并返回 lastrowid。"""
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def execute_many(sql: str, seq: list[tuple]) -> None:
    with get_conn() as conn:
        conn.executemany(sql, seq)
