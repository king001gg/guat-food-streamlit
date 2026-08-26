"""投稿：普通用户投稿进入待审核，管理员直接上架。"""
import streamlit as st

from core import db, files
from core import session as sess
from services import dishes, windows

user = sess.current_user()
if not user:
    st.info("请先登录后再投稿")
    if st.button("去登录"):
        st.switch_page("app_pages/login.py")
    st.stop()

is_admin = sess.is_admin()
status = "PUBLISHED" if is_admin else "PENDING"

kind = st.segmented_control(
    "投稿类型", ["WINDOW", "DISH"], format_func=lambda v: "档口" if v == "WINDOW" else "菜品", default="WINDOW"
)

canteens = db.query("SELECT id, name FROM canteen ORDER BY sort_order, id")

if kind == "WINDOW":
    with st.form("submit_window"):
        name = st.text_input("档口名称")
        canteen_choice = st.selectbox("所属食堂", [c["name"] for c in canteens])
        location = st.text_input("位置（如 一楼）")
        description = st.text_area("简介")
        cover = st.file_uploader("封面图", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("提交投稿", width="stretch")
    if submitted:
        if not name.strip():
            st.error("请填写档口名称")
        else:
            cid = next(c["id"] for c in canteens if c["name"] == canteen_choice)
            windows.create(
                cid, name.strip(), description.strip(), files.save_image(cover), location.strip(), user["id"], status
            )
            st.toast("已提交，等待管理员审核" if status == "PENDING" else "已直接上架")
            st.rerun()
else:
    win_list = windows.list_published()
    # 空列表时给占位选项，避免 selectbox 因无选项报错；提交时再校验
    win_names = [w["name"] for w in win_list] or ["（暂无已上架档口，请选「自定义新档口」）"]

    # 所属档口支持自定义：可从已有档口选择，也可直接填写新档口
    src = st.segmented_control("档口来源", ["已有档口", "自定义新档口"], default="已有档口")

    with st.form("submit_dish"):
        name = st.text_input("菜品名称")
        if src == "已有档口":
            window_choice = st.selectbox("所属档口", win_names)
        else:
            new_canteen = st.selectbox("新档口所属食堂", [c["name"] for c in canteens])
            new_window_name = st.text_input("新档口名称", placeholder="如 二楼螺蛳粉")
            new_window_location = st.text_input("新档口位置（选填）", placeholder="如 一楼")
        price = st.number_input("价格（元）", min_value=0.0, max_value=200.0, step=0.5, value=10.0)
        description = st.text_area("简介")
        image = st.file_uploader("图片", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("提交投稿", width="stretch")

    if submitted:
        if not name.strip():
            st.error("请填写菜品名称")
        elif src == "已有档口" and not win_list:
            st.error("暂无已上架的档口，请切换为「自定义新档口」")
        elif src == "自定义新档口" and not new_window_name.strip():
            st.error("请填写新档口名称")
        else:
            if src == "已有档口":
                wid = next(w["id"] for w in win_list if w["name"] == window_choice)
            else:
                cid = next(c["id"] for c in canteens if c["name"] == new_canteen)
                wid = windows.get_or_create(
                    cid, new_window_name.strip(), user["id"], status, new_window_location.strip()
                )
            dishes.create(
                wid, name.strip(), description.strip(), files.save_image(image), price, user["id"], status
            )
            st.toast("已提交，等待管理员审核" if status == "PENDING" else "已直接上架")
            st.rerun()
