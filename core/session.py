"""会话状态与权限（UI 层，依赖 Streamlit）。"""
from __future__ import annotations

import streamlit as st


def init_session() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("detail_target", None)  # {"type": "WINDOW"/"DISH", "id": int}
    st.session_state.setdefault("viewed_targets", set())
    st.session_state.setdefault("pending_nav", None)  # 待切换页面路径


def current_user() -> dict | None:
    return st.session_state.get("user")


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("role") == "ADMIN")


def do_login(user: dict) -> None:
    st.session_state.user = user


def do_logout() -> None:
    st.session_state.user = None
    st.session_state.detail_target = None


def set_detail_target(target_type: str, target_id: int) -> None:
    st.session_state.detail_target = {"type": target_type, "id": target_id}


def handle_nav() -> None:
    """消费待切换页面标记（由 ButtonColumn 回调设置），执行页面跳转。"""
    target = st.session_state.get("pending_nav")
    if target:
        st.session_state.pending_nav = None
        st.switch_page(target)
