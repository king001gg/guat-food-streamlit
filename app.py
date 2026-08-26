"""桂航美食推荐排行榜 —— 入口与多页面导航。"""
import streamlit as st

from core import db, seed, ui
from core import session as sess

st.set_page_config(page_title="桂航美食推荐排行榜", page_icon="🚀", layout="wide")

db.init_db()
seed.seed_if_empty()
sess.init_session()
ui.inject_theme()

pages = [
    st.Page("app_pages/home.py", title="榜单首页", icon=":material/leaderboard:", default=True),
    st.Page("app_pages/window_detail.py", title="档口详情", icon=":material/storefront:"),
    st.Page("app_pages/dish_detail.py", title="菜品详情", icon=":material/restaurant:"),
    st.Page("app_pages/login.py", title="登录 / 注册", icon=":material/login:"),
    st.Page("app_pages/profile.py", title="个人中心", icon=":material/person:"),
    st.Page("app_pages/submit.py", title="投稿", icon=":material/playlist_add:"),
]
if sess.is_admin():
    pages.append(st.Page("app_pages/admin.py", title="后台管理", icon=":material/admin_panel_settings:"))

page = st.navigation(pages, position="sidebar")

with st.sidebar:
    st.markdown("### 🚀 桂航美食榜")
    user = sess.current_user()
    if user:
        st.markdown(f"**{user['nickname']}**  ·  {'管理员' if user['role'] == 'ADMIN' else '普通用户'}")
        if st.button("退出登录", width="stretch"):
            sess.do_logout()
            st.rerun()
    else:
        st.caption("未登录 · 浏览榜单无需登录")

# 首页由 hero 横幅承担视觉标题，其余页面保留通用页头
if page.title != "榜单首页":
    st.title(f"{page.icon} {page.title}")

page.run()
ui.footer()
