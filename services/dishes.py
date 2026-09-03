"""菜品业务。"""
from __future__ import annotations

from core import db
from services import rankings


def get_dish(dish_id: int, increment_view: bool = False) -> dict | None:
    if increment_view:
        db.execute("UPDATE dish SET view_count = view_count + 1 WHERE id = ?", (dish_id,))
    return rankings.get_dish_row(dish_id)


def list_admin() -> list[dict]:
    return db.query(
        """
        SELECT d.*, w.name AS window_name, c.name AS canteen_name
        FROM dish d
        JOIN food_window w ON w.id = d.window_id
        JOIN canteen c ON c.id = w.canteen_id
        ORDER BY d.id
        """
    )


def list_published(window_id: int | None = None) -> list[dict]:
    sql = "SELECT id, name FROM dish WHERE status = 'PUBLISHED'"
    params: list = []
    if window_id:
        sql += " AND window_id = ?"
        params.append(window_id)
    sql += " ORDER BY name"
    return db.query(sql, tuple(params))


def pending() -> list[dict]:
    return db.query(
        """
        SELECT d.*, w.name AS window_name, c.name AS canteen_name
        FROM dish d
        JOIN food_window w ON w.id = d.window_id
        JOIN canteen c ON c.id = w.canteen_id
        WHERE d.status = 'PENDING' ORDER BY d.id
        """
    )


def create(
    window_id: int,
    name: str,
    description: str,
    image: str | None,
    price: float,
    submitter_id: int | None,
    status: str,
) -> int:
    return db.execute(
        "INSERT INTO dish (window_id, submitter_id, name, description, image, price, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (window_id, submitter_id, name, description, image, price, status),
    )


def set_status(dish_id: int, status: str) -> None:
    db.execute(
        "UPDATE dish SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (status, dish_id),
    )


def update(dish_id: int, name: str, description: str, price: float, window_id: int | None = None) -> None:
    if window_id is None:
        db.execute(
            "UPDATE dish SET name = ?, description = ?, price = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (name, description, price, dish_id),
        )
    else:
        db.execute(
            "UPDATE dish SET window_id = ?, name = ?, description = ?, price = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (window_id, name, description, price, dish_id),
        )


def delete(dish_id: int) -> None:
    db.execute("DELETE FROM rating WHERE target_type = 'DISH' AND target_id = ?", (dish_id,))
    db.execute("DELETE FROM like_record WHERE target_type = 'DISH' AND target_id = ?", (dish_id,))
    db.execute("DELETE FROM favorite WHERE target_type = 'DISH' AND target_id = ?", (dish_id,))
    db.execute("DELETE FROM dish WHERE id = ?", (dish_id,))
