"""榜单聚合与排序：SQL 聚合 + 算法排序，供首页与后台使用。"""
from __future__ import annotations

from core import db
from core.algorithms import RANKERS, compute_heat

_WINDOW_SELECT = """
SELECT
  w.id, w.name, w.canteen_id, w.description, w.cover_image, w.location, w.status, w.view_count,
  c.name AS canteen_name,
  COUNT(DISTINCT r.id) AS rating_count,
  AVG(r.taste) AS taste_avg,
  AVG(r.value_score) AS value_avg,
  AVG(r.portion) AS portion_avg,
  COUNT(DISTINCT l.id) AS like_count,
  COUNT(DISTINCT f.id) AS favorite_count,
  COUNT(DISTINCT CASE WHEN r.created_at >= datetime('now', 'localtime', '-30 days') THEN r.id END) AS recent_count
FROM food_window w
JOIN canteen c ON c.id = w.canteen_id
LEFT JOIN rating r ON r.target_type = 'WINDOW' AND r.target_id = w.id
LEFT JOIN like_record l ON l.target_type = 'WINDOW' AND l.target_id = w.id
LEFT JOIN favorite f ON f.target_type = 'WINDOW' AND f.target_id = w.id
"""

_DISH_SELECT = """
SELECT
  d.id, d.name, d.window_id, d.description, d.image, d.price, d.status, d.view_count,
  w.name AS window_name, c.id AS canteen_id, c.name AS canteen_name,
  COUNT(DISTINCT r.id) AS rating_count,
  AVG(r.taste) AS taste_avg,
  AVG(r.value_score) AS value_avg,
  AVG(r.portion) AS portion_avg,
  COUNT(DISTINCT l.id) AS like_count,
  COUNT(DISTINCT f.id) AS favorite_count,
  COUNT(DISTINCT CASE WHEN r.created_at >= datetime('now', 'localtime', '-30 days') THEN r.id END) AS recent_count
FROM dish d
JOIN food_window w ON w.id = d.window_id
JOIN canteen c ON c.id = w.canteen_id
LEFT JOIN rating r ON r.target_type = 'DISH' AND r.target_id = d.id
LEFT JOIN like_record l ON l.target_type = 'DISH' AND l.target_id = d.id
LEFT JOIN favorite f ON f.target_type = 'DISH' AND f.target_id = d.id
"""

# PostgreSQL 要求 GROUP BY 列出所有非聚合列（SQLite 允许裸列），这里显式展开以便双后端共用。
_WINDOW_GROUP = "w.id, w.name, w.canteen_id, w.description, w.cover_image, w.location, w.status, w.view_count, c.name"
_DISH_GROUP = "d.id, d.name, d.window_id, d.description, d.image, d.price, d.status, d.view_count, w.name, c.id, c.name"


def _postprocess(rows: list[dict]) -> list[dict]:
    for r in rows:
        taste = r.get("taste_avg") or 0
        value = r.get("value_avg") or 0
        portion = r.get("portion_avg") or 0
        r["taste_avg"] = round(taste, 2)
        r["value_avg"] = round(value, 2)
        r["portion_avg"] = round(portion, 2)
        r["score_avg"] = round((taste + value + portion) / 3, 2)
        r["heat"] = compute_heat(r)
    return rows


def get_rankings(
    target_type: str,
    rank_type: str = "overall",
    canteen_id: int | None = None,
    window_id: int | None = None,
    keyword: str | None = None,
    limit: int = 50,
) -> list[dict]:
    rank_type = rank_type if rank_type in RANKERS else "overall"
    keyword = (keyword or "").strip()

    if target_type == "WINDOW":
        sql = _WINDOW_SELECT
        where = ["w.status = 'PUBLISHED'"]
        params: list = []
        if canteen_id:
            where.append("w.canteen_id = ?")
            params.append(canteen_id)
        if keyword:
            where.append("(w.name LIKE ? OR w.description LIKE ?)")
            params += [f"%{keyword}%", f"%{keyword}%"]
        group = _WINDOW_GROUP
    else:
        sql = _DISH_SELECT
        where = ["d.status = 'PUBLISHED'"]
        params = []
        if canteen_id:
            where.append("c.id = ?")
            params.append(canteen_id)
        if window_id:
            where.append("d.window_id = ?")
            params.append(window_id)
        if keyword:
            where.append("(d.name LIKE ? OR d.description LIKE ?)")
            params += [f"%{keyword}%", f"%{keyword}%"]
        group = _DISH_GROUP

    sql = sql + " WHERE " + " AND ".join(where) + f" GROUP BY {group}"
    rows = _postprocess(db.query(sql, tuple(params)))
    return RANKERS[rank_type](rows)[:limit]


def get_window_row(window_id: int) -> dict | None:
    rows = db.query(_WINDOW_SELECT + " WHERE w.id = ? GROUP BY " + _WINDOW_GROUP, (window_id,))
    return _postprocess(rows)[0] if rows else None


def get_dish_row(dish_id: int) -> dict | None:
    rows = db.query(_DISH_SELECT + " WHERE d.id = ? GROUP BY " + _DISH_GROUP, (dish_id,))
    return _postprocess(rows)[0] if rows else None
