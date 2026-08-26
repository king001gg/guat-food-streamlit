# -*- coding: utf-8 -*-
"""桂航美食榜 · 安全与认证专项测试（输入归一化 + 种子密码来源）。

覆盖本次新增的两处改动：
  1. core/auth.py 的 _normalize_input：全角/空白归一化，及其与 bcrypt 72 字节边界的交互
  2. core/seed.py 的密码来源：环境变量 > .streamlit/secrets.toml > 随机兜底

用法：  py qa_security_test.py
隔离：  独立临时库，不污染真实 data/guatfood.db。
"""
import os
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import db, seed, auth

_tmpdir = Path(tempfile.mkdtemp(prefix="guat_qa_sec_"))
db.DB_PATH = _tmpdir / "test.db"
db.init_db()
seed.seed_if_empty()

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


# ---------------- 归一化单元 ----------------
def _t_norm_halfwidth():
    eq(auth._normalize_input("ｌｄｓ６６６６６６"), "lds666666", "全角字母数字应转半角")
    eq(auth._normalize_input("guihanxiaoxiaol"), "guihanxiaoxiaol", "半角应原样返回")
    eq(auth._normalize_input("ｇｕｉｈａｎｘｉａｏｘｉａｏｌ"), "guihanxiaoxiaol", "全角用户名应转半角")


check("归一化：全角转半角", _t_norm_halfwidth)


def _t_norm_whitespace():
    eq(auth._normalize_input("  abc  "), "abc", "应去除首尾空白")
    eq(auth._normalize_input("abc　def"), "abc def", "全角空格应转半角空格")
    eq(auth._normalize_input("密码１２３"), "密码123", "中文应保留、全角数字应转半角")
    eq(auth._normalize_input(None), "", "None 应返回空串")
    eq(auth._normalize_input(""), "", "空串应返回空串")


check("归一化：空白/全角空格/中文/None", _t_norm_whitespace)


# ---------------- 注册 / 登录 归一化 ----------------
def _t_register_normalizes():
    ok_flag, _ = auth.register_user("ｑａｕｓｅｒ１", "ｐａｓｓ１２３", "全角用户")
    eq(ok_flag, True, "全角用户名/密码应注册成功")
    u = auth.authenticate("qauser1", "pass123")[0]
    ok(u is not None and u["username"] == "qauser1", "注册后应用半角用户名+密码登录")


check("注册归一化：全角注册→半角登录", _t_register_normalizes)


def _t_login_normalizes():
    auth.register_user("normuser", "normpass", "n")
    ok(auth.authenticate(" normuser ", " normpass ")[0] is not None, "带首尾空格登录应成功")
    ok(auth.authenticate("ｎｏｒｍｕｓｅｒ", "ｎｏｒｍｐａｓｓ")[0] is not None, "全角登录应成功")
    ok(auth.authenticate("normuser", "WRONG")[0] is None, "错误密码仍应失败")


check("登录归一化：空格/全角/错误密码", _t_login_normalizes)


# ---------------- bcrypt 72 字节边界 × 归一化 ----------------
def _t_norm_bcrypt_boundary():
    # 24 个全角字母 = 72 字节；归一化后 24 字节，应能注册
    ok_flag, _ = auth.register_user("fullwidth72", "ａ" * 24, "f")
    eq(ok_flag, True, "24 个全角字母归一化后应可注册")
    # 73 个半角字节仍应被拒绝
    ok_flag2, _ = auth.register_user("long73", "a" * 73, "f")
    eq(ok_flag2, False, "73 字节半角密码应被拒绝")


check("bcrypt 72 字节边界（含归一化收缩）", _t_norm_bcrypt_boundary)


def _t_empty_password():
    ok(auth.authenticate("guihanxiaoxiaol", "")[0] is None, "空密码应登录失败")
    ok(auth.authenticate("", "")[0] is None, "空用户名+空密码应登录失败")


check("空密码/空用户名登录安全", _t_empty_password)


# ---------------- 种子密码来源 ----------------
def _t_seed_admin_username():
    row = db.query_one("SELECT username, role FROM user WHERE role='ADMIN'")
    eq(row["username"], "guihanxiaoxiaol", "种子管理员用户名应为 guihanxiaoxiaol")
    eq(row["role"], "ADMIN", "角色应为 ADMIN")


check("种子管理员用户名/角色", _t_seed_admin_username)


def _t_load_secrets_valid():
    good = _tmpdir / "good.toml"
    good.write_text('ADMIN_PASSWORD = "abc123"\nDEMO_PASSWORD = "demo"\n', encoding="utf-8")
    old = seed._SECRETS_PATH
    seed._SECRETS_PATH = good
    try:
        eq(seed._load_secrets(), {"ADMIN_PASSWORD": "abc123", "DEMO_PASSWORD": "demo"}, "应正确解析 TOML")
    finally:
        seed._SECRETS_PATH = old


check("secrets.toml 有效解析", _t_load_secrets_valid)


def _t_load_secrets_graceful():
    old = seed._SECRETS_PATH
    try:
        seed._SECRETS_PATH = _tmpdir / "nope.toml"
        eq(seed._load_secrets(), {}, "缺失文件应返回空 dict")
        bad = _tmpdir / "bad.toml"
        bad.write_text("this is [[[ not valid toml", encoding="utf-8")
        seed._SECRETS_PATH = bad
        eq(seed._load_secrets(), {}, "损坏 TOML 应返回空 dict 而不抛异常")
    finally:
        seed._SECRETS_PATH = old


check("secrets.toml 缺失/损坏优雅降级", _t_load_secrets_graceful)


def _t_resolve_priority():
    os.environ["ADMIN_PASSWORD"] = "envpass123"
    try:
        eq(seed._resolve_password("ADMIN_PASSWORD", {"ADMIN_PASSWORD": "secretpass"}), "envpass123", "env 应优先于 secrets")
    finally:
        del os.environ["ADMIN_PASSWORD"]
    eq(seed._resolve_password("ADMIN_PASSWORD", {"ADMIN_PASSWORD": "secretpass"}), "secretpass", "secrets 应兜底")


check("密码解析优先级 env > secrets", _t_resolve_priority)


def _t_resolve_random():
    r1 = seed._resolve_password("UNSET_KEY_1", {})
    r2 = seed._resolve_password("UNSET_KEY_1", {})
    ok(r1 and len(r1) > 10, "随机密码应非空且足够长")
    ok(r1 != r2, "两次随机密码不应相同")


check("未配置时生成随机密码", _t_resolve_random)


def _t_seed_uses_env_password():
    os.environ["ADMIN_PASSWORD"] = "admin_env_pw"
    os.environ["DEMO_PASSWORD"] = "demo_env_pw"
    old_db = db.DB_PATH
    db.DB_PATH = _tmpdir / "seed_env.db"
    try:
        db.init_db()
        seed.seed_if_empty()
        ok(auth.authenticate("guihanxiaoxiaol", "admin_env_pw")[0] is not None, "种子管理员应用 env 密码")
        ok(auth.authenticate("zhangsan", "demo_env_pw")[0] is not None, "种子演示用户应用 env 密码")
    finally:
        del os.environ["ADMIN_PASSWORD"]
        del os.environ["DEMO_PASSWORD"]
        db.DB_PATH = old_db


check("全新种子使用环境变量密码（集成）", _t_seed_uses_env_password)


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
