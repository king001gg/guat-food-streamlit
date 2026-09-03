"""后台统计与用户/食堂管理。"""
from __future__ import annotations

from core import db
from services import rankings


def overview() -> dict:
    def count(sql: str, params: tuple = ()) -> int:
        row = db.query_one(sql, params)
        return row["c"] if row else 0

    canteen_stats = db.query(
        """
        SELECT c.id, c.name, c.location,
               (SELECT COUNT(*) FROM food_window w WHERE w.canteen_id = c.id) AS window_count,
               (SELECT COUNT(*) FROM dish d JOIN food_window w2 ON w2.id = d.window_id
                WHERE w2.canteen_id = c.id) AS dish_count
        FROM canteen c ORDER BY c.sort_order, c.id
        """
    )

    rating_dist = db.query(
        "SELECT taste, COUNT(*) AS c FROM rating GROUP BY taste ORDER BY taste"
    )

    top_windows = rankings.get_rankings("WINDOW", "heat", limit=10)
    top_dishes = rankings.get_rankings("DISH", "heat", limit=10)

    return {
        "users": count("SELECT COUNT(*) AS c FROM user"),
        "canteens": count("SELECT COUNT(*) AS c FROM canteen"),
        "windows": count("SELECT COUNT(*) AS c FROM food_window"),
        "dishes": count("SELECT COUNT(*) AS c FROM dish"),
        "ratings": count("SELECT COUNT(*) AS c FROM rating"),
        "likes": count("SELECT COUNT(*) AS c FROM like_record"),
        "favorites": count("SELECT COUNT(*) AS c FROM favorite"),
        "pending_windows": count("SELECT COUNT(*) AS c FROM food_window WHERE status = 'PENDING'"),
        "pending_dishes": count("SELECT COUNT(*) AS c FROM dish WHERE status = 'PENDING'"),
        "canteen_stats": canteen_stats,
        "rating_dist": rating_dist,
        "top_windows": top_windows,
        "top_dishes": top_dishes,
    }


def list_users() -> list[dict]:
    return db.query("SELECT id, username, nickname, role, status, created_at FROM user ORDER BY id")


def set_user_status(user_id: int, status: str) -> None:
    db.execute("UPDATE user SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?", (status, user_id))


def set_user_role(user_id: int, role: str) -> None:
    db.execute("UPDATE user SET role = ?, updated_at = datetime('now', 'localtime') WHERE id = ?", (role, user_id))


def delete_user(user_id: int) -> None:
    db.execute("DELETE FROM rating WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM like_record WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM favorite WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM user WHERE id = ?", (user_id,))


def list_canteens() -> list[dict]:
    return db.query("SELECT * FROM canteen ORDER BY sort_order, id")


def create_canteen(name: str, location: str, sort_order: int) -> int:
    return db.execute("INSERT INTO canteen (name, location, sort_order) VALUES (?, ?, ?)", (name, location, sort_order))


def update_canteen(canteen_id: int, name: str, location: str, sort_order: int) -> None:
    db.execute(
        "UPDATE canteen SET name = ?, location = ?, sort_order = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (name, location, sort_order, canteen_id),
    )


def delete_canteen(canteen_id: int) -> None:
    from services import windows

    for wid in [r["id"] for r in db.query("SELECT id FROM food_window WHERE canteen_id = ?", (canteen_id,))]:
        windows.delete(wid)
    db.execute("DELETE FROM canteen WHERE id = ?", (canteen_id,))
