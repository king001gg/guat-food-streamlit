"""排行榜算法（纯函数，输入带聚合字段的 dict 列表，输出排序结果）。

每个元素需包含的字段（由 services.rankings 预计算）：
- score_avg / taste_avg：三维均分与口味均分
- rating_count / like_count / view_count / recent_count
"""
from __future__ import annotations


def compute_heat(row: dict) -> float:
    """人气值 = 评分数×10 + 点赞数×5 + 浏览量。"""
    return row.get("rating_count", 0) * 10 + row.get("like_count", 0) * 5 + row.get("view_count", 0)


def rank_overall(rows: list[dict]) -> list[dict]:
    """综合榜：三维平均分降序，同分按评分数降序。"""
    return sorted(
        rows,
        key=lambda r: (r.get("score_avg", 0), r.get("rating_count", 0)),
        reverse=True,
    )


def rank_taste(rows: list[dict]) -> list[dict]:
    """好评榜：口味均分降序，同分按评分数降序。"""
    return sorted(
        rows,
        key=lambda r: (r.get("taste_avg", 0), r.get("rating_count", 0)),
        reverse=True,
    )


def rank_heat(rows: list[dict]) -> list[dict]:
    """人气榜：按人气值降序。"""
    return sorted(rows, key=compute_heat, reverse=True)


def rank_recent(rows: list[dict]) -> list[dict]:
    """热门榜：近 30 天评分数降序。"""
    return sorted(rows, key=lambda r: r.get("recent_count", 0), reverse=True)


RANKERS = {
    "overall": rank_overall,
    "taste": rank_taste,
    "heat": rank_heat,
    "recent": rank_recent,
}

RANK_LABELS = {
    "overall": "综合榜",
    "taste": "好评榜",
    "heat": "人气榜",
    "recent": "热门榜",
}
