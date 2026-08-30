# -*- coding: utf-8 -*-
"""桂航美食榜 · PostgreSQL 翻译层纯函数测试（无需真实 PG 库）。

覆盖 core.db 的 _adapt_sql（SQLite 方言 → PostgreSQL）、_pg_schema()（建表 schema 转换）
以及 execute 在 PG 后端对 INSERT 拼接 RETURNING id 的逻辑。

用法：  py qa_pg_sql_test.py
"""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import db

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


def _has(s, sub, msg=""):
    assert sub in s, f"{msg} 未找到 {sub!r}"


def _not_has(s, sub, msg=""):
    assert sub not in s, f"{msg} 不应包含 {sub!r}"


# ---------------- _adapt_sql：方言翻译 ----------------
def _t_placeholder():
    out = db._adapt_sql("SELECT * FROM dish WHERE id = ? AND name LIKE ?")
    _has(out, "%s", "占位符 ? 应转成 %s")
    _not_has(out, "?", "占位符不应残留 ?")
    eq(out.count("%s"), 2, "两处占位符都应转换")


check("占位符 ? → %s", _t_placeholder)


def _t_date_now():
    out = db._adapt_sql("... datetime('now', 'localtime') ...")
    _has(out, "CURRENT_TIMESTAMP", "应转为 CURRENT_TIMESTAMP")
    _not_has(out, "datetime(", "不应残留 datetime(")


check("datetime('now','localtime') → CURRENT_TIMESTAMP", _t_date_now)


def _t_date_30d():
    # 长串先替换，避免被短串吃掉
    out = db._adapt_sql("datetime('now', 'localtime', '-30 days')")
    eq(out, "CURRENT_TIMESTAMP - INTERVAL '30 days'", "近 30 天应完整转换，且不含残留")
    _not_has(out, "datetime(", "不应残留 datetime(")


check("近 30 天 datetime → INTERVAL", _t_date_30d)


def _t_like():
    out = db._adapt_sql("WHERE name LIKE ? OR description LIKE ?")
    eq(out.count(" ILIKE "), 2, "两处 LIKE 都应转 ILIKE")
    _not_has(out, " LIKE ", "不应残留 LIKE")


check("LIKE → ILIKE", _t_like)


def _t_quote_user():
    out = db._adapt_sql(
        "SELECT u.* FROM user u JOIN rating r ON r.user_id = u.id "
        "WHERE u.username = ? AND r.user_id = ?"
    )
    _has(out, '"user"', "表名 user 应加双引号")
    _has(out, "r.user_id", "user_id 不应被改写")
    _has(out, "u.username", "username 不应被改写")
    _not_has(out, '"username"', "username 不应加引号")
    _not_has(out, '"user_id"', "user_id 不应加引号")


check("表名 user 加引号且不误伤 user_id/username", _t_quote_user)


# ---------------- _pg_schema：建表 schema 转换 ----------------
def _t_pg_schema():
    s = db._pg_schema()
    _not_has(s, "AUTOINCREMENT", "不应残留 AUTOINCREMENT")
    _not_has(s, "datetime(", "不应残留 datetime(")
    _not_has(s, "REAL DEFAULT", "不应残留 REAL DEFAULT")
    _has(s, "SERIAL PRIMARY KEY", "主键应转 SERIAL")
    _has(s, "TIMESTAMPTZ", "时间列应转 TIMESTAMPTZ")
    _has(s, "DOUBLE PRECISION DEFAULT 0", "price 应转 DOUBLE PRECISION")
    _has(s, 'CREATE TABLE IF NOT EXISTS "user"', "user 表名应加双引号")
    _has(s, "DEFAULT 'USER'", "角色默认字面量 USER 应保持大写原样")


check("_pg_schema 转换完整", _t_pg_schema)


def _t_pg_schema_statements():
    stmts = [x.strip() for x in db._pg_schema().split(";") if x.strip()]
    tables = [x for x in stmts if x.upper().startswith("CREATE TABLE")]
    eq(len(tables), 7, "应有 7 张表")
    # 每张表名都应合法（无残留 SQLite 函数、无裸 user 保留字）
    for stmt in stmts:
        _not_has(stmt, "AUTOINCREMENT", "语句残留 AUTOINCREMENT")
        ok("datetime(" not in stmt, "语句残留 datetime(")


check("_pg_schema 可拆成 7 张表且无残留方言", _t_pg_schema_statements)


# ---------------- execute：PG 下 INSERT 拼 RETURNING id ----------------
def _t_execute_pg_returning():
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

    captured = {}

    class _FakeRows:
        def fetchone(self):
            return {"id": 77}

    class _FakeConn:
        def execute(self, sql, params=()):
            captured["sql"] = sql
            captured["params"] = params
            return _FakeRows()

    @contextmanager
    def _fake_get_conn():
        yield _FakeConn()

    old_get_conn = db.get_conn
    db.get_conn = _fake_get_conn
    try:
        rid = db.execute(
            "INSERT INTO user (username, password, nickname, role, status) VALUES (?, ?, ?, ?, 'ACTIVE')",
            ("u", "p", "n"),
        )
    finally:
        db.get_conn = old_get_conn
        os.environ.pop("DATABASE_URL", None)

    eq(rid, 77, "PG 下 INSERT 应返回 RETURNING id")
    _has(captured["sql"], "RETURNING id", "应拼接 RETURNING id")
    _has(captured["sql"], '"user"', "INSERT 目标表 user 应加引号")
    _has(captured["sql"], "%s", "占位符应为 %s")
    eq(captured["params"], ("u", "p", "n"), "参数应原样传递")


check("execute(PG) INSERT 拼 RETURNING id", _t_execute_pg_returning)


def _t_execute_pg_update_no_returning():
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

    captured = {}

    class _FakeConn:
        def execute(self, sql, params=()):
            captured["sql"] = sql
            return None

    @contextmanager
    def _fake_get_conn():
        yield _FakeConn()

    old_get_conn = db.get_conn
    db.get_conn = _fake_get_conn
    try:
        rid = db.execute("UPDATE user SET status = ? WHERE id = ?", ("DISABLED", 3))
    finally:
        db.get_conn = old_get_conn
        os.environ.pop("DATABASE_URL", None)

    eq(rid, None, "PG 下 UPDATE 应返回 None")
    _not_has(captured["sql"], "RETURNING id", "UPDATE 不应拼接 RETURNING id")


check("execute(PG) UPDATE 不拼 RETURNING id", _t_execute_pg_update_no_returning)


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
