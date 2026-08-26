# -*- coding: utf-8 -*-
"""桂航美食榜 · 自动化测试（单元 + 服务层）。

用法：  py qa_test.py
隔离： 通过把 db.DB_PATH 指向临时文件，不污染真实 data/guatfood.db。
"""
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import db

_tmpdir = tempfile.mkdtemp(prefix="guat_qa_")
db.DB_PATH = Path(_tmpdir) / "test.db"

db.init_db()
from core import seed

seed.seed_if_empty()

from core import algorithms, auth
from services import admin as admin_svc
from services import dishes, interactions, rankings, ratings, windows

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, "PASS", ""))
    except AssertionError as e:
        RESULTS.append((name, "FAIL", str(e)))
    except Exception as e:  # noqa: BLE001
        RESULTS.append((name, "ERROR", f"{type(e).__name__}: {e}"))


def eq(a, b, msg=""):
    assert a == b, f"{msg} 期望={b!r} 实际={a!r}"


def ok(x, msg=""):
    assert x, msg or "条件不成立"


# ---------------- 算法 ----------------
check("compute_heat 计算公式", lambda: eq(algorithms.compute_heat(
    {"rating_count": 2, "like_count": 3, "view_count": 4}), 39))


def _t_rank_overall():
    rows = [
        {"id": 1, "score_avg": 4.0, "rating_count": 5},
        {"id": 2, "score_avg": 4.5, "rating_count": 1},
        {"id": 3, "score_avg": 4.0, "rating_count": 9},
    ]
    got = algorithms.rank_overall(rows)
    eq([r["id"] for r in got], [2, 3, 1], "综合榜应分数降序、同分按评分数降序")


check("rank_overall 排序", _t_rank_overall)


def _t_rank_heat():
    rows = [
        {"id": 1, "rating_count": 1, "like_count": 0, "view_count": 0},
        {"id": 2, "rating_count": 0, "like_count": 3, "view_count": 0},
        {"id": 3, "rating_count": 0, "like_count": 0, "view_count": 100},
    ]
    got = algorithms.rank_heat(rows)
    eq([r["id"] for r in got], [3, 2, 1], "人气值 100 > 15 > 10")


check("rank_heat 排序", _t_rank_heat)


def _t_rank_recent():
    rows = [{"id": 1, "recent_count": 2}, {"id": 2, "recent_count": 9}, {"id": 3, "recent_count": 2}]
    eq([r["id"] for r in algorithms.rank_recent(rows)], [2, 1, 3])


check("rank_recent 排序", _t_rank_recent)

# ---------------- 认证 ----------------
check("注册合法用户", lambda: eq(auth.register_user("testuser1", "secret1", "测试员")[0], True))
check("注册用户名过短", lambda: eq(auth.register_user("ab", "secret1", "")[0], False))
check("注册用户名含非法字符", lambda: eq(auth.register_user("bad name", "secret1", "")[0], False))
check("注册密码过短", lambda: eq(auth.register_user("testuser2", "123", "")[0], False))
check("注册重复用户名", lambda: eq(auth.register_user("testuser1", "secret2", "")[0], False))


def _t_register_long_password():
    # 30 个中文字符 = 90 字节，超过 bcrypt 72 字节上限；应被优雅拒绝而非抛异常
    ok_flag, _msg = auth.register_user("longpwuser", "密" * 30, "长密码")
    eq(ok_flag, False, "超长密码应注册失败")


check("注册超长密码(90字节)不应崩溃", _t_register_long_password)

check("登录正确", lambda: eq(auth.authenticate("testuser1", "secret1")[0]["username"], "testuser1"))
check("登录密码错误", lambda: eq(auth.authenticate("testuser1", "wrongpw")[0], None))


def _t_authenticate_disabled():
    uid = auth.get_user(auth.authenticate("testuser1", "secret1")[0]["id"])["id"]
    admin_svc.set_user_status(uid, "DISABLED")
    eq(auth.authenticate("testuser1", "secret1")[1], "账号已被禁用")


check("禁用账号不能登录", _t_authenticate_disabled)

# ---------------- 评分 ----------------
check("评分插入", lambda: ok(ratings.upsert_rating(1, "DISH", 1, 5, 4, 4, "好吃") is None))


def _t_rating_upsert():
    ratings.upsert_rating(2, "DISH", 900001, 5, 5, 5, "首次")
    ratings.upsert_rating(2, "DISH", 900001, 1, 1, 1, "改评")
    agg = ratings.aggregate("DISH", 900001)
    eq(agg["rating_count"], 1, "upsert 应覆盖而非新增")
    eq(agg["taste_avg"], 1.0, "覆盖后口味应更新")


check("评分 upsert 覆盖", _t_rating_upsert)

check("user_rating 未评返回 None", lambda: eq(ratings.user_rating(999, "DISH", 1), None))
check("list_ratings 带昵称", lambda: ok(all("nickname" in r for r in ratings.list_ratings("DISH", 1))))


def _t_aggregate_empty():
    a = ratings.aggregate("DISH", 99999)
    eq(a["rating_count"], 0)
    eq(a["score_avg"], 0.0)


check("aggregate 无评分返回零值", _t_aggregate_empty)

# ---------------- 点赞 / 收藏 ----------------
def _t_toggle():
    first = interactions.toggle_like(6, "WINDOW", 900002)
    second = interactions.toggle_like(6, "WINDOW", 900002)
    third = interactions.toggle_like(6, "WINDOW", 900002)
    eq((first, second, third), (True, False, True), "toggle 应在 赞/取消 间切换")


check("点赞 toggle 语义", _t_toggle)


def _t_favorite_count():
    interactions.toggle_favorite(3, "WINDOW", 1)
    interactions.toggle_favorite(4, "WINDOW", 1)
    eq(interactions.favorite_count("WINDOW", 1), 2, "收藏计数")


check("收藏计数", _t_favorite_count)

check("my_favorites 返回列表", lambda: ok(isinstance(interactions.my_favorites(1), list)))

# ---------------- 档口 ----------------
def _t_get_or_create():
    cid = db.query_one("SELECT id FROM canteen ORDER BY sort_order, id LIMIT 1")["id"]
    a = windows.get_or_create(cid, "QA自定义档口", 1, "PENDING", "一楼")
    b = windows.get_or_create(cid, "QA自定义档口", 2, "PENDING", "二楼")
    eq(a, b, "同食堂同名应复用同一档口")


check("get_or_create 复用", _t_get_or_create)


def _t_window_lifecycle():
    cid = db.query_one("SELECT id FROM canteen ORDER BY sort_order, id LIMIT 1")["id"]
    wid = windows.create(cid, "QA档口", "desc", None, "三楼", 1, "PENDING")
    ok(wid and wid > 0, "创建返回 id")
    eq(wid in [w["id"] for w in windows.pending()], True, "待审核应包含新档口")
    windows.set_status(wid, "PUBLISHED")
    eq(wid in [w["id"] for w in windows.list_published(cid)], True, "上架后出现在已发布列表")


check("档口创建/审核/上架", _t_window_lifecycle)


def _t_window_delete_cascade():
    cid = db.query_one("SELECT id FROM canteen ORDER BY sort_order, id LIMIT 1")["id"]
    wid = windows.create(cid, "QA待删档口", "desc", None, "三楼", 1, "PUBLISHED")
    did = dishes.create(wid, "QA待删菜品", "desc", None, 10.0, 1, "PUBLISHED")
    windows.delete(wid)
    eq(dishes.get_dish(did), None, "删除档口应级联删除其菜品")


check("删除档口级联删除菜品", _t_window_delete_cascade)

# ---------------- 菜品 ----------------
def _t_dish_lifecycle():
    wid = db.query_one("SELECT id FROM food_window WHERE status='PUBLISHED' LIMIT 1")["id"]
    did = dishes.create(wid, "QA菜品", "desc", None, 9.9, 1, "PENDING")
    eq(did in [d["id"] for d in dishes.pending()], True, "待审核应包含新菜品")
    dishes.set_status(did, "PUBLISHED")
    eq(did in [d["id"] for d in dishes.list_published(wid)], True, "上架后出现在列表")
    dishes.delete(did)
    eq(dishes.get_dish(did), None, "删除后查询不到")


check("菜品创建/审核/上架/删除", _t_dish_lifecycle)

# ---------------- 榜单聚合 ----------------
def _t_rankings_ordered():
    rows = rankings.get_rankings("WINDOW", "overall")
    ok(len(rows) > 0, "应有数据")
    ok(all(r["status"] == "PUBLISHED" for r in rows), "只返回已发布")
    scores = [r["score_avg"] for r in rows]
    eq(scores, sorted(scores, reverse=True), "综合榜应分数降序")


check("榜单只含已发布且按分数降序", _t_rankings_ordered)


def _t_rankings_filter():
    cid = db.query_one("SELECT id FROM canteen ORDER BY sort_order, id LIMIT 1")["id"]
    rows = rankings.get_rankings("WINDOW", "overall", canteen_id=cid)
    ok(all(r["canteen_id"] == cid for r in rows), "按食堂过滤")
    kw = rankings.get_rankings("WINDOW", "overall", keyword="螺蛳粉")
    ok(all(("螺蛳粉" in (r["name"] or "")) or ("螺蛳粉" in (r["description"] or "")) for r in kw), "关键词过滤")


check("榜单按食堂/关键词过滤", _t_rankings_filter)


def _t_ranking_excludes_pending():
    cid = db.query_one("SELECT id FROM canteen ORDER BY sort_order, id LIMIT 1")["id"]
    wid = windows.create(cid, "QA审核中档口", "desc", None, "三楼", 1, "PENDING")
    eq(wid in [r["id"] for r in rankings.get_rankings("WINDOW")], False, "待审核不应进榜")
    windows.delete(wid)


check("待审核不进榜单", _t_ranking_excludes_pending)

check("get_window_row 含综合分", lambda: ok("score_avg" in rankings.get_window_row(1)))
check("get_dish_row 含综合分", lambda: ok("score_avg" in rankings.get_dish_row(1)))

# ---------------- 后台 ----------------
def _t_overview():
    o = admin_svc.overview()
    for k in ["users", "canteens", "windows", "dishes", "ratings", "pending_windows", "pending_dishes", "top_windows", "top_dishes"]:
        ok(k in o, f"缺 key {k}")


check("后台概览字段齐全", _t_overview)


def _t_canteen_duplicate():
    name = "QA重复食堂"
    admin_svc.create_canteen(name, "位置", 99)
    try:
        admin_svc.create_canteen(name, "位置", 99)
        raise AssertionError("重复食堂名应抛异常（由页面 try/except 捕获）")
    except Exception:
        pass


check("食堂名唯一约束", _t_canteen_duplicate)

# ---------------- 汇总 ----------------
print("\n" + "=" * 60)
passed = sum(1 for r in RESULTS if r[1] == "PASS")
failed = sum(1 for r in RESULTS if r[1] == "FAIL")
errored = sum(1 for r in RESULTS if r[1] == "ERROR")
for name, status, detail in RESULTS:
    mark = {"PASS": "✔", "FAIL": "✘", "ERROR": "⚠"}[status]
    line = f"[{mark} {status:5}] {name}"
    if detail:
        line += f"  -> {detail}"
    print(line)
print("=" * 60)
print(f"总计 {len(RESULTS)} 项：通过 {passed}，失败 {failed}，异常 {errored}")
sys.exit(1 if (failed or errored) else 0)
