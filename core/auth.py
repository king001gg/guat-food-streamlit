"""认证业务逻辑（纯逻辑 + 数据库，不依赖 Streamlit）。"""
from __future__ import annotations

import re

import bcrypt

from core import db

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _normalize_input(s: str) -> str:
    """归一化输入：去除首尾空白，并把全角 ASCII 转为半角。

    中文输入法常在数字/字母上误用全角（如 ６、ｌ），导致登录失败；
    登录与注册统一归一化，避免这类「看着一样、字节不同」的输入问题。
    """
    s = (s or "").strip()
    out = []
    for ch in s:
        cp = ord(ch)
        if cp == 0x3000:  # 全角空格 -> 半角空格
            out.append(" ")
        elif 0xFF01 <= cp <= 0xFF5E:  # 全角 ASCII -> 半角
            out.append(chr(cp - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def register_user(username: str, password: str, nickname: str) -> tuple[bool, str]:
    username = _normalize_input(username)
    password = _normalize_input(password)
    nickname = (nickname or "").strip() or username
    if not USERNAME_RE.fullmatch(username):
        return False, "用户名需为 3-20 位字母、数字或下划线"
    if len(password) < 6:
        return False, "密码至少 6 位"
    if len(password.encode("utf-8")) > 72:
        # bcrypt 仅支持 72 字节以内的密码，超出会抛 ValueError
        return False, "密码过长，最多 72 字节（约 24 个汉字）"
    if db.query_one("SELECT id FROM user WHERE username = ?", (username,)):
        return False, "用户名已存在"
    db.execute(
        "INSERT INTO user (username, password, nickname, role, status) "
        "VALUES (?, ?, ?, 'USER', 'ACTIVE')",
        (username, hash_password(password), nickname),
    )
    return True, "注册成功，请登录"


def authenticate(username: str, password: str) -> tuple[dict | None, str]:
    username = _normalize_input(username)
    password = _normalize_input(password)
    user = db.query_one("SELECT * FROM user WHERE username = ?", (username,))
    if not user or not verify_password(password, user["password"]):
        return None, "用户名或密码错误"
    if user["status"] != "ACTIVE":
        return None, "账号已被禁用"
    public = {
        "id": user["id"],
        "username": user["username"],
        "nickname": user["nickname"],
        "role": user["role"],
        "avatar": user["avatar"],
    }
    return public, "登录成功"


def update_profile(user_id: int, nickname: str, avatar: str | None = None) -> None:
    if avatar is None:
        db.execute(
            "UPDATE user SET nickname = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (nickname, user_id),
        )
    else:
        db.execute(
            "UPDATE user SET nickname = ?, avatar = ?, updated_at = datetime('now', 'localtime') "
            "WHERE id = ?",
            (nickname, avatar, user_id),
        )


def get_user(user_id: int) -> dict | None:
    return db.query_one("SELECT * FROM user WHERE id = ?", (user_id,))
