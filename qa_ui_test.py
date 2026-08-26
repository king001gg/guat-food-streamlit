# -*- coding: utf-8 -*-
"""桂航美食榜 · 页面集成测试 + 端到端业务流程测试。

用法：  py qa_ui_test.py
隔离：  同样把 db.DB_PATH 指向临时文件。
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

_tmpdir = tempfile.mkdtemp(prefix="guat_qa_ui_")
db.DB_PATH = Path(_tmpdir) / "test.db"

db.init_db()
from core import seed

seed.seed_if_empty()

from streamlit.testing.v1 import AppTest  # noqa: E402
from core import auth  # noqa: E402
from services import admin as admin_svc  # noqa: E402
from services import dishes, interactions, rankings, ratings, windows  # noqa: E402

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


def _seed_user(at, uid, role="USER"):
    at.session_state["user"] = {
        "id": uid, "username": "u%d" % uid, "nickname": "用户%d" % uid, "role": role, "avatar": None,
    }


# ---------------- 页面渲染 ----------------
def _home():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    ok(not at.exception, "首页不应有异常")
    btns = [b for b in at.button if "查看详情" in (b.label or "")]
    ok(len(btns) >= 1, "首页应有榜单卡片「查看详情」按钮")


check("首页渲染（入口 app.py）", _home)


def _home_switch_dish():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.segmented_control[0].set_value("DISH").run()
    ok(not at.exception, "切到菜品榜不应有异常")


check("首页切换菜品榜", _home_switch_dish)


def _nav_window():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    btns = [b for b in at.button if "查看详情" in (b.label or "")]
    btns[0].click().run()
    ok(not at.exception, "档口详情跳转不应有异常")
    ok(any(s.value for s in at.subheader), "档口详情应有标题")


check("档口详情跳转", _nav_window)


def _nav_dish():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.segmented_control[0].set_value("DISH").run()
    btns = [b for b in at.button if "查看详情" in (b.label or "")]
    btns[0].click().run()
    ok(not at.exception, "菜品详情跳转不应有异常")


check("菜品详情跳转", _nav_dish)


def _login_render():
    at = AppTest.from_file("app_pages/login.py", default_timeout=30).run()
    ok(not at.exception, "登录页不应有异常")
    ok(len(at.text_input) >= 4, "登录页应有登录/注册输入框")


check("登录页渲染", _login_render)


def _detail_window_render():
    at = AppTest.from_file("app_pages/window_detail.py", default_timeout=30)
    at.session_state["detail_target"] = {"type": "WINDOW", "id": 1}
    at.session_state["viewed_targets"] = set()
    at.run()
    ok(not at.exception, "档口详情不应有异常")
    ok(len(at.metric) >= 5, "档口详情应有 5 个指标")


check("档口详情渲染", _detail_window_render)


def _detail_dish_render():
    at = AppTest.from_file("app_pages/dish_detail.py", default_timeout=30)
    at.session_state["detail_target"] = {"type": "DISH", "id": 1}
    at.session_state["viewed_targets"] = set()
    at.run()
    ok(not at.exception, "菜品详情不应有异常")
    ok(len(at.metric) >= 5, "菜品详情应有 5 个指标")


check("菜品详情渲染", _detail_dish_render)


def _profile_render():
    at = AppTest.from_file("app_pages/profile.py", default_timeout=30)
    _seed_user(at, 2)
    at.run()
    ok(not at.exception, "个人中心不应有异常")


check("个人中心渲染", _profile_render)


def _submit_render():
    at = AppTest.from_file("app_pages/submit.py", default_timeout=30)
    _seed_user(at, 2)
    at.run()
    ok(not at.exception, "投稿（档口）不应有异常")
    at.segmented_control[0].set_value("DISH").run()
    ok(not at.exception, "投稿（菜品）不应有异常")
    at.segmented_control[1].set_value("自定义新档口").run()
    ok(not at.exception, "投稿（自定义新档口）不应有异常")
    ok(any("新档口名称" in (t.label or "") for t in at.text_input), "自定义模式应有「新档口名称」输入框")


check("投稿页渲染（档口/菜品/自定义档口）", _submit_render)


def _admin_render():
    at = AppTest.from_file("app_pages/admin.py", default_timeout=60)
    _seed_user(at, 1, role="ADMIN")
    at.run()
    ok(not at.exception, "后台管理不应有异常")


check("后台管理渲染（管理员）", _admin_render)


def _admin_blocked():
    at = AppTest.from_file("app_pages/admin.py", default_timeout=30)
    _seed_user(at, 2, role="USER")
    at.run()
    ok(any("无权访问" in (e.value or "") for e in at.error), "普通用户访问后台应被拦截")


check("后台权限拦截（普通用户）", _admin_blocked)

# ---------------- 端到端业务流程 ----------------
def _e2e_flow():
    # 1. 注册 + 登录
    ok(auth.register_user("e2euser", "e2epass", "E2E用户")[0], "注册失败")
    u = auth.authenticate("e2euser", "e2epass")[0]
    ok(u is not None, "登录失败")
    uid = u["id"]

    # 2. 普通用户投稿档口 → 待审核
    cid = db.query_one("SELECT id FROM canteen ORDER BY sort_order, id LIMIT 1")["id"]
    wid = windows.create(cid, "E2E测试档口", "E2E简介", None, "一楼", uid, "PENDING")
    eq(wid in [r["id"] for r in rankings.get_rankings("WINDOW")], False, "待审核不应进榜")

    # 3. 管理员审核通过 → 进榜
    windows.set_status(wid, "PUBLISHED")
    found = rankings.get_rankings("WINDOW", "overall", keyword="E2E测试档口")
    ok(any(r["id"] == wid for r in found), "审核通过后应能进榜")

    # 4. 详情聚合：未评分时综合分为 0
    row = rankings.get_window_row(wid)
    eq(row["score_avg"], 0.0, "无评分综合分应为 0")

    # 5. 评分 → 聚合更新
    ratings.upsert_rating(uid, "WINDOW", wid, 5, 4, 4, "很好")
    row2 = rankings.get_window_row(wid)
    eq(row2["rating_count"], 1, "评分后评分数应为 1")
    eq(row2["taste_avg"], 5.0, "口味均分应为 5")

    # 6. 点赞 + 收藏
    ok(interactions.toggle_like(uid, "WINDOW", wid) is True, "点赞应为已赞")
    ok(interactions.toggle_favorite(uid, "WINDOW", wid) is True, "收藏应为已收藏")
    eq(interactions.like_count("WINDOW", wid), 1)
    eq(interactions.favorite_count("WINDOW", wid), 1)
    ok(any(f["target_id"] == wid for f in interactions.my_favorites(uid)), "我的收藏应包含该档口")
    ok(any(r["target_id"] == wid for r in ratings.my_ratings(uid)), "我的评分应包含该档口")

    # 7. 菜品挂在该档口下
    did = dishes.create(wid, "E2E测试菜品", "desc", None, 15.0, uid, "PUBLISHED")
    eq(rankings.get_dish_row(did)["window_name"], "E2E测试档口", "菜品应归属该档口")

    # 清理
    dishes.delete(did)
    windows.delete(wid)
    admin_svc.delete_user(uid)


check("端到端：注册→投稿→审核→进榜→详情→评分→点赞/收藏", _e2e_flow)

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
