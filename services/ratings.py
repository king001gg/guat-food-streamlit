"""评分业务。"""
from __future__ import annotations

import streamlit as st

from core import db


def upsert_rating(
    user_id: int,
    target_type: str,
    target_id: int,
    taste: int,
    value_score: int,
    portion: int,
    comment: str,
) -> None:
    db.execute(
        """
        INSERT INTO rating (user_id, target_type, target_id, taste, value_score, portion, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, target_type, target_id)
        DO UPDATE SET taste = excluded.taste,
                      value_score = excluded.value_score,
                      portion = excluded.portion,
                      comment = excluded.comment,
                      created_at = datetime('now', 'localtime')
        """,
        (user_id, target_type, target_id, taste, value_score, portion, (comment or "").strip()),
    )
    st.cache_data.clear()


def list_ratings(target_type: str, target_id: int) -> list[dict]:
    return db.query(
        """
        SELECT r.*, u.nickname, u.avatar
        FROM rating r JOIN user u ON u.id = r.user_id
        WHERE r.target_type = ? AND r.target_id = ?
        ORDER BY r.created_at DESC, r.id DESC
        """,
        (target_type, target_id),
    )


def user_rating(user_id: int, target_type: str, target_id: int) -> dict | None:
    return db.query_one(
        "SELECT * FROM rating WHERE user_id = ? AND target_type = ? AND target_id = ?",
        (user_id, target_type, target_id),
    )


def aggregate(target_type: str, target_id: int) -> dict:
    row = db.query_one(
        """
        SELECT COUNT(*) AS rating_count,
               AVG(taste) AS taste_avg,
               AVG(value_score) AS value_avg,
               AVG(portion) AS portion_avg
        FROM rating WHERE target_type = ? AND target_id = ?
        """,
        (target_type, target_id),
    )
    if not row or not row["rating_count"]:
        return {"rating_count": 0, "taste_avg": 0.0, "value_avg": 0.0, "portion_avg": 0.0, "score_avg": 0.0}
    taste, value, portion = row["taste_avg"], row["value_avg"], row["portion_avg"]
    return {
        "rating_count": row["rating_count"],
        "taste_avg": round(taste, 2),
        "value_avg": round(value, 2),
        "portion_avg": round(portion, 2),
        "score_avg": round((taste + value + portion) / 3, 2),
    }


def my_ratings(user_id: int) -> list[dict]:
    windows = db.query(
        """
        SELECT r.*, w.name AS target_name
        FROM rating r JOIN food_window w ON w.id = r.target_id
        WHERE r.user_id = ? AND r.target_type = 'WINDOW'
        """,
        (user_id,),
    )
    dishes = db.query(
        """
        SELECT r.*, d.name AS target_name
        FROM rating r JOIN dish d ON d.id = r.target_id
        WHERE r.user_id = ? AND r.target_type = 'DISH'
        """,
        (user_id,),
    )
    rows = windows + dishes
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows


def delete_rating(rating_id: int) -> None:
    db.execute("DELETE FROM rating WHERE id = ?", (rating_id,))
    st.cache_data.clear()
