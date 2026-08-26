"""登录与注册。"""
import streamlit as st

from core import auth
from core import session as sess

if sess.current_user():
    st.success(f"已登录：{sess.current_user()['nickname']}（{sess.current_user()['username']}）")
    if st.button("退出登录"):
        sess.do_logout()
        st.rerun()
    st.stop()

tab_login, tab_register = st.tabs(["登录", "注册"])

with tab_login:
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password", max_chars=72)
        submitted = st.form_submit_button("登录", width="stretch")
    if submitted:
        user, msg = auth.authenticate(username, password)
        if user:
            sess.do_login(user)
            st.switch_page("app_pages/home.py")
        else:
            st.error(msg)

with tab_register:
    with st.form("register_form"):
        username = st.text_input("用户名", help="3-20 位字母、数字或下划线")
        nickname = st.text_input("昵称（可选）")
        password = st.text_input("密码", type="password", max_chars=72, help="至少 6 位，最多 72 字节（约 24 个汉字）")
        submitted = st.form_submit_button("注册", width="stretch")
    if submitted:
        ok, msg = auth.register_user(username, password, nickname)
        if ok:
            st.success(msg)
        else:
            st.error(msg)
