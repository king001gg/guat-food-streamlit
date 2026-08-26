"""首次启动种子数据：演示账号 / 食堂 / 档口 / 菜品 / 评分 / 点赞 / 收藏。

数据沿用参考项目（guat-food-recommendations）的 DataInitializer。
种子密码不写死在仓库中：优先读环境变量，其次读本地 .streamlit/secrets.toml。
"""
from __future__ import annotations

import os
import secrets as _secrets
import tomllib

from core import db
from core.auth import hash_password

_SECRETS_PATH = db.ROOT / ".streamlit" / "secrets.toml"


def _load_secrets() -> dict:
    """读取本地 .streamlit/secrets.toml（TOML，已 gitignore），失败返回空。"""
    if not _SECRETS_PATH.exists():
        return {}
    try:
        with open(_SECRETS_PATH, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _resolve_password(env_key: str, secrets: dict) -> str:
    """优先环境变量，其次 secrets.toml；都未配置则生成随机密码并打印提示。"""
    pwd = os.environ.get(env_key) or secrets.get(env_key)
    if pwd:
        return str(pwd)
    random_pw = _secrets.token_urlsafe(9)
    print(f"[seed] {env_key} not set, generated random password: {random_pw}")
    return random_pw

_USERS = [
    ("guihanxiaoxiaol", "管理员", "ADMIN"),
    ("zhangsan", "张三", "USER"),
    ("lisi", "李四", "USER"),
    ("wangwu", "王五", "USER"),
    ("zhaoliu", "赵六", "USER"),
    ("sunqi", "孙七", "USER"),
]

_CANTEENS = [
    ("天舟楼食堂", "南校区", 1),
    ("天宫楼食堂", "北校区", 2),
    ("莘子苑食堂", "东校区", 3),
    ("校外", "商业街", 4),
]

# (canteen_idx, name, description, location)
_WINDOWS = [
    (1, "桂林米粉", "桂林本地米粉，卤水香浓，锅烧脆香", "一楼"),
    (1, "柳州螺蛳粉", "酸辣鲜香，配料十足，汤底浓郁", "一楼"),
    (1, "自选快餐", "荤素自选，经济实惠，两荤一素管饱", "二楼"),
    (2, "麻辣香锅", "现炒香锅，麻辣过瘾，可自选菜品", "一楼"),
    (2, "黄焖鸡米饭", "鸡肉嫩滑，汤汁拌饭一绝", "一楼"),
    (2, "兰州拉面", "手工拉面，汤清面劲，牛肉大块", "二楼"),
    (3, "烤肉拌饭", "蜜汁烤肉，酱香浓郁，份量十足", "一楼"),
    (3, "石锅拌饭", "韩式石锅，锅巴香脆，酱料地道", "二楼"),
    (4, "港式烧腊", "叉烧烧鸭，皮脆肉嫩，港味正宗", "一楼"),
    (4, "糖水铺", "广式糖水，清甜解腻，下午茶首选", "一楼"),
]

# (window_idx, name, description, price)
_DISHES = [
    (1, "桂林米粉", "招牌桂林米粉，锅烧+叉烧", 8.00),
    (1, "卤菜粉", "多卤菜版本，料足味浓", 9.00),
    (2, "招牌螺蛳粉", "酸笋+腐竹+花生，汤底浓郁", 12.00),
    (2, "干捞螺蛳粉", "无汤版本，酱香更浓", 13.00),
    (3, "两荤一素套餐", "自选两荤一素，米饭管饱", 12.00),
    (4, "麻辣香锅(自选)", "自选食材现炒，麻辣鲜香", 15.00),
    (5, "黄焖鸡米饭", "嫩滑鸡肉+浓香汤汁", 14.00),
    (6, "牛肉拉面", "手工拉面，大块牛肉", 12.00),
    (7, "蜜汁烤肉饭", "蜜汁烤肉，酱香四溢", 13.00),
    (8, "五花肉石锅拌饭", "锅巴香脆，韩式辣酱", 16.00),
    (9, "叉烧饭", "蜜汁叉烧，肥瘦相间", 18.00),
    (10, "杨枝甘露", "芒果+西柚，清甜解暑", 10.00),
]

# (username, target_type, target_idx, taste, value_score, portion, comment)
_RATINGS = [
    ("zhangsan", "WINDOW", 1, 5, 4, 4, "米粉很正宗，锅烧特别脆"),
    ("lisi", "WINDOW", 1, 5, 5, 4, "性价比高，饭点排队也值"),
    ("wangwu", "WINDOW", 1, 4, 4, 4, "味道不错，就是汤有点咸"),
    ("zhaoliu", "WINDOW", 1, 5, 4, 5, "量足味道好"),
    ("sunqi", "WINDOW", 1, 4, 4, 3, "还不错"),
    ("zhangsan", "WINDOW", 2, 5, 3, 4, "螺蛳粉天花板，酸笋很够味"),
    ("lisi", "WINDOW", 2, 4, 3, 4, "好吃但略贵"),
    ("wangwu", "WINDOW", 2, 5, 4, 5, "配料很多，汤底浓郁"),
    ("zhaoliu", "WINDOW", 2, 4, 3, 4, "中规中矩"),
    ("zhangsan", "WINDOW", 3, 3, 5, 4, "便宜管饱，口味一般"),
    ("lisi", "WINDOW", 3, 3, 5, 5, "性价比之王"),
    ("wangwu", "WINDOW", 3, 3, 4, 4, "食堂打菜阿姨手不抖"),
    ("zhangsan", "WINDOW", 4, 4, 3, 4, "香锅味道可以，就是贵了点"),
    ("lisi", "WINDOW", 4, 5, 3, 4, "麻辣鲜香，每次都要排队"),
    ("zhaoliu", "WINDOW", 4, 4, 3, 3, "还行"),
    ("zhangsan", "WINDOW", 5, 5, 4, 4, "黄焖鸡yyds，汤汁拌饭绝了"),
    ("lisi", "WINDOW", 5, 5, 4, 5, "鸡肉嫩，分量足"),
    ("wangwu", "WINDOW", 5, 4, 4, 4, "好吃不贵"),
    ("sunqi", "WINDOW", 5, 5, 4, 4, "每周必吃"),
    ("lisi", "WINDOW", 6, 4, 4, 4, "拉面筋道，牛肉也不少"),
    ("wangwu", "WINDOW", 6, 4, 4, 5, "汤很鲜"),
    ("zhaoliu", "WINDOW", 6, 3, 3, 3, "一般般，偏咸"),
    ("zhangsan", "WINDOW", 7, 4, 4, 5, "烤肉饭量大，酱香浓郁"),
    ("lisi", "WINDOW", 7, 5, 4, 5, "蜜汁烤肉一绝"),
    ("sunqi", "WINDOW", 7, 4, 4, 4, "好吃"),
    ("wangwu", "WINDOW", 8, 4, 3, 4, "锅巴很脆，酱料地道"),
    ("zhaoliu", "WINDOW", 8, 4, 3, 3, "还行，稍贵"),
    ("zhangsan", "WINDOW", 8, 3, 3, 3, "一般"),
    ("lisi", "WINDOW", 9, 4, 3, 3, "叉烧不错，就是贵"),
    ("wangwu", "WINDOW", 9, 5, 3, 4, "烧鸭皮很脆"),
    ("sunqi", "WINDOW", 9, 4, 3, 3, "味道可以"),
    ("zhangsan", "WINDOW", 10, 4, 4, 3, "糖水清甜，适合下午"),
    ("zhaoliu", "WINDOW", 10, 5, 4, 4, "杨枝甘露很好喝"),
    ("sunqi", "WINDOW", 10, 4, 4, 3, "不错"),
    ("zhangsan", "DISH", 1, 5, 4, 4, "锅烧很脆，卤水香"),
    ("lisi", "DISH", 1, 5, 5, 4, "最爱的桂林米粉"),
    ("wangwu", "DISH", 1, 4, 4, 4, "味道不错"),
    ("lisi", "DISH", 2, 4, 4, 4, "卤菜很多"),
    ("zhaoliu", "DISH", 2, 4, 4, 4, "还可以"),
    ("zhangsan", "DISH", 3, 5, 3, 4, "螺蛳粉一定要点这个"),
    ("lisi", "DISH", 3, 5, 3, 4, "汤底很浓郁"),
    ("sunqi", "DISH", 3, 4, 3, 4, "不错"),
    ("wangwu", "DISH", 4, 4, 3, 4, "干捞更入味"),
    ("zhaoliu", "DISH", 4, 4, 3, 4, "可以"),
    ("zhangsan", "DISH", 5, 3, 5, 4, "便宜实惠"),
    ("lisi", "DISH", 5, 3, 5, 5, "管饱"),
    ("zhangsan", "DISH", 6, 4, 3, 4, "香锅不错"),
    ("lisi", "DISH", 6, 5, 3, 4, "麻辣过瘾"),
    ("zhangsan", "DISH", 7, 5, 4, 4, "黄焖鸡yyds"),
    ("lisi", "DISH", 7, 5, 4, 5, "汤汁拌饭绝了"),
    ("wangwu", "DISH", 7, 4, 4, 4, "好吃"),
    ("lisi", "DISH", 8, 4, 4, 4, "牛肉大块"),
    ("wangwu", "DISH", 8, 4, 4, 5, "汤很鲜"),
    ("zhangsan", "DISH", 9, 5, 4, 5, "蜜汁烤肉饭量大"),
    ("lisi", "DISH", 9, 5, 4, 5, "酱香浓郁"),
    ("wangwu", "DISH", 10, 4, 3, 4, "锅巴脆"),
    ("zhaoliu", "DISH", 10, 4, 3, 3, "还行"),
    ("lisi", "DISH", 11, 4, 3, 3, "叉烧不错"),
    ("wangwu", "DISH", 11, 5, 3, 4, "烧鸭皮脆"),
    ("zhangsan", "DISH", 12, 4, 4, 3, "好喝"),
    ("zhaoliu", "DISH", 12, 5, 4, 4, "杨枝甘露yyds"),
    ("sunqi", "DISH", 12, 4, 4, 3, "清甜"),
]

# (username, target_type, target_idx)
_LIKES = [
    ("zhangsan", "WINDOW", 1), ("lisi", "WINDOW", 1), ("wangwu", "WINDOW", 1),
    ("zhangsan", "WINDOW", 2), ("lisi", "WINDOW", 2),
    ("zhangsan", "WINDOW", 5), ("lisi", "WINDOW", 5), ("wangwu", "WINDOW", 5),
    ("zhangsan", "WINDOW", 7), ("lisi", "WINDOW", 7),
    ("zhangsan", "DISH", 1), ("lisi", "DISH", 1),
    ("zhangsan", "DISH", 3), ("lisi", "DISH", 3),
    ("zhangsan", "DISH", 7), ("lisi", "DISH", 7),
    ("zhangsan", "DISH", 9), ("lisi", "DISH", 9),
]

_FAVORITES = [
    ("zhangsan", "WINDOW", 1),
    ("zhangsan", "WINDOW", 2),
    ("lisi", "WINDOW", 1),
    ("lisi", "DISH", 7),
    ("zhangsan", "DISH", 9),
]


def seed_if_empty() -> None:
    db.init_db()
    # 以「食堂表」作为内容是否已初始化的信号：即使已有用户，只要食堂/档口等为空，仍补种演示数据。
    if db.query_one("SELECT id FROM canteen LIMIT 1"):
        return
    _seed()


def _seed() -> None:
    secrets = _load_secrets()
    hashed_demo = hash_password(_resolve_password("DEMO_PASSWORD", secrets))
    hashed_admin = hash_password(_resolve_password("ADMIN_PASSWORD", secrets))

    # 用户/食堂：幂等插入（避免与已注册用户或已存在食堂冲突），随后按名称回查 id
    for username, nickname, role in _USERS:
        hashed = hashed_admin if role == "ADMIN" else hashed_demo
        db.execute(
            "INSERT OR IGNORE INTO user (username, password, nickname, role, status) "
            "VALUES (?, ?, ?, ?, 'ACTIVE')",
            (username, hashed, nickname, role),
        )
    user_ids = {u["username"]: u["id"] for u in db.query("SELECT id, username FROM user")}

    for name, location, sort_order in _CANTEENS:
        db.execute(
            "INSERT OR IGNORE INTO canteen (name, location, sort_order) VALUES (?, ?, ?)",
            (name, location, sort_order),
        )
    canteen_id_of = {c["name"]: c["id"] for c in db.query("SELECT id, name FROM canteen")}
    canteen_ids = [canteen_id_of[name] for name, _, _ in _CANTEENS]

    window_ids = []
    for canteen_idx, name, description, location in _WINDOWS:
        window_ids.append(
            db.execute(
                "INSERT INTO food_window (canteen_id, name, description, location, status) "
                "VALUES (?, ?, ?, ?, 'PUBLISHED')",
                (canteen_ids[canteen_idx - 1], name, description, location),
            )
        )

    dish_ids = []
    for window_idx, name, description, price in _DISHES:
        dish_ids.append(
            db.execute(
                "INSERT INTO dish (window_id, name, description, price, status) "
                "VALUES (?, ?, ?, ?, 'PUBLISHED')",
                (window_ids[window_idx - 1], name, description, price),
            )
        )

    for username, target_type, idx, taste, value, portion, comment in _RATINGS:
        target_id = window_ids[idx - 1] if target_type == "WINDOW" else dish_ids[idx - 1]
        db.execute(
            "INSERT INTO rating (user_id, target_type, target_id, taste, value_score, portion, comment) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_ids[username], target_type, target_id, taste, value, portion, comment),
        )

    for username, target_type, idx in _LIKES:
        target_id = window_ids[idx - 1] if target_type == "WINDOW" else dish_ids[idx - 1]
        db.execute(
            "INSERT INTO like_record (user_id, target_type, target_id) VALUES (?, ?, ?)",
            (user_ids[username], target_type, target_id),
        )

    for username, target_type, idx in _FAVORITES:
        target_id = window_ids[idx - 1] if target_type == "WINDOW" else dish_ids[idx - 1]
        db.execute(
            "INSERT INTO favorite (user_id, target_type, target_id) VALUES (?, ?, ?)",
            (user_ids[username], target_type, target_id),
        )
