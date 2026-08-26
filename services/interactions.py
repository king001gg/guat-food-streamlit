"""点赞与收藏（toggle 语义）。"""
from __future__ import annotations

from core import db


def _toggle(table: str, user_id: int, target_type: str, target_id: int) -> bool:
    """切换点赞/收藏状态，返回切换后的状态（True=已点/已收藏）。"""
    existing = db.query_one(
        f"SELECT id FROM {table} WHERE user_id = ? AND target_type = ? AND target_id = ?",
        (user_id, target_type, target_id),
    )
    if existing:
        db.execute(f"DELETE FROM {table} WHERE id = ?", (existing["id"],))
        return False
    db.execute(
        f"INSERT INTO {table} (user_id, target_type, target_id) VALUES (?, ?, ?)",
        (user_id, target_type, target_id),
    )
    return True


def _exists(table: str, user_id: int, target_type: str, target_id: int) -> bool:
    row = db.query_one(
        f"SELECT id FROM {table} WHERE user_id = ? AND target_type = ? AND target_id = ?",
        (user_id, target_type, target_id),
    )
    return row is not None


def _count(table: str, target_type: str, target_id: int) -> int:
    row = db.query_one(
        f"SELECT COUNT(*) AS c FROM {table} WHERE target_type = ? AND target_id = ?",
        (target_type, target_id),
    )
    return row["c"] if row else 0


def toggle_like(user_id: int, target_type: str, target_id: int) -> bool:
    return _toggle("like_record", user_id, target_type, target_id)


def toggle_favorite(user_id: int, target_type: str, target_id: int) -> bool:
    return _toggle("favorite", user_id, target_type, target_id)


def is_liked(user_id: int, target_type: str, target_id: int) -> bool:
    return _exists("like_record", user_id, target_type, target_id)


def is_favorited(user_id: int, target_type: str, target_id: int) -> bool:
    return _exists("favorite", user_id, target_type, target_id)


def like_count(target_type: str, target_id: int) -> int:
    return _count("like_record", target_type, target_id)


def favorite_count(target_type: str, target_id: int) -> int:
    return _count("favorite", target_type, target_id)


def my_favorites(user_id: int) -> list[dict]:
    windows = db.query(
        """
        SELECT f.*, w.name AS target_name, w.cover_image AS image
        FROM favorite f JOIN food_window w ON w.id = f.target_id
        WHERE f.user_id = ? AND f.target_type = 'WINDOW'
        """,
        (user_id,),
    )
    dishes = db.query(
        """
        SELECT f.*, d.name AS target_name, d.image
        FROM favorite f JOIN dish d ON d.id = f.target_id
        WHERE f.user_id = ? AND f.target_type = 'DISH'
        """,
        (user_id,),
    )
    rows = windows + dishes
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows
