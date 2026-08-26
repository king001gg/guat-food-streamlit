"""档口业务。"""
from __future__ import annotations

from core import db
from services import rankings


def get_window(window_id: int, increment_view: bool = False) -> dict | None:
    if increment_view:
        db.execute("UPDATE food_window SET view_count = view_count + 1 WHERE id = ?", (window_id,))
    return rankings.get_window_row(window_id)


def list_admin() -> list[dict]:
    return db.query(
        """
        SELECT w.*, c.name AS canteen_name
        FROM food_window w JOIN canteen c ON c.id = w.canteen_id
        ORDER BY w.id
        """
    )


def list_published(canteen_id: int | None = None) -> list[dict]:
    sql = "SELECT id, name FROM food_window WHERE status = 'PUBLISHED'"
    params: list = []
    if canteen_id:
        sql += " AND canteen_id = ?"
        params.append(canteen_id)
    sql += " ORDER BY name"
    return db.query(sql, tuple(params))


def pending() -> list[dict]:
    return db.query(
        """
        SELECT w.*, c.name AS canteen_name
        FROM food_window w JOIN canteen c ON c.id = w.canteen_id
        WHERE w.status = 'PENDING' ORDER BY w.id
        """
    )


def create(
    canteen_id: int,
    name: str,
    description: str,
    cover_image: str | None,
    location: str,
    submitter_id: int | None,
    status: str,
) -> int:
    return db.execute(
        "INSERT INTO food_window (canteen_id, submitter_id, name, description, cover_image, location, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (canteen_id, submitter_id, name, description, cover_image, location, status),
    )


def get_or_create(
    canteen_id: int,
    name: str,
    submitter_id: int | None,
    status: str,
    location: str = "",
) -> int:
    """按「食堂 + 档口名」查找已有档口，存在则复用其 id，否则新建（菜品投稿自定义档口用）。"""
    existing = db.query_one(
        "SELECT id FROM food_window WHERE canteen_id = ? AND name = ? LIMIT 1",
        (canteen_id, name),
    )
    if existing:
        return existing["id"]
    return create(canteen_id, name, "", None, location, submitter_id, status)


def set_status(window_id: int, status: str) -> None:
    db.execute(
        "UPDATE food_window SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (status, window_id),
    )


def delete(window_id: int) -> None:
    for did in [r["id"] for r in db.query("SELECT id FROM dish WHERE window_id = ?", (window_id,))]:
        db.execute("DELETE FROM rating WHERE target_type = 'DISH' AND target_id = ?", (did,))
        db.execute("DELETE FROM like_record WHERE target_type = 'DISH' AND target_id = ?", (did,))
        db.execute("DELETE FROM favorite WHERE target_type = 'DISH' AND target_id = ?", (did,))
    db.execute("DELETE FROM dish WHERE window_id = ?", (window_id,))
    db.execute("DELETE FROM rating WHERE target_type = 'WINDOW' AND target_id = ?", (window_id,))
    db.execute("DELETE FROM like_record WHERE target_type = 'WINDOW' AND target_id = ?", (window_id,))
    db.execute("DELETE FROM favorite WHERE target_type = 'WINDOW' AND target_id = ?", (window_id,))
    db.execute("DELETE FROM food_window WHERE id = ?", (window_id,))
