"""个人中心：资料、我的评分、我的收藏、我的投稿。"""
import pandas as pd
import streamlit as st

from core import auth, db
from core import session as sess
from services import interactions, ratings

sess.handle_nav()

user = sess.current_user()
if not user:
    st.info("请先登录")
    if st.button("去登录"):
        st.switch_page("app_pages/login.py")
    st.stop()

st.subheader("个人资料")
with st.form("profile_form"):
    nickname = st.text_input("昵称", value=user["nickname"] or "")
    submitted = st.form_submit_button("保存")
if submitted:
    nick = (nickname or "").strip()
    if not nick:
        st.error("昵称不能为空")
    else:
        auth.update_profile(user["id"], nick)
        sess.do_login({**user, "nickname": nick})
        st.toast("已保存")
        st.rerun()

tab_ratings, tab_favorites, tab_submissions = st.tabs(["我的评分", "我的收藏", "我的投稿"])

with tab_ratings:
    rows = ratings.my_ratings(user["id"])
    if not rows:
        st.caption("暂无评分")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "类型": "档口" if r["target_type"] == "WINDOW" else "菜品",
                        "名称": r["target_name"],
                        "口味": r["taste"],
                        "性价比": r["value_score"],
                        "分量": r["portion"],
                        "评语": r["comment"] or "",
                        "时间": r["created_at"],
                    }
                    for r in rows
                ]
            ),
            hide_index=True,
        )

with tab_favorites:
    favs = interactions.my_favorites(user["id"])
    if not favs:
        st.caption("暂无收藏")
    else:
        fav_df = pd.DataFrame(
            [
                {
                    "类型": "档口" if f["target_type"] == "WINDOW" else "菜品",
                    "名称": f["target_name"],
                    "收藏时间": f["created_at"],
                    "操作": "查看",
                }
                for f in favs
            ]
        )

        def open_fav():
            click = st.session_state.get("fav_click")
            if click and click.get("row") is not None:
                f = favs[click["row"]]
                sess.set_detail_target(f["target_type"], f["target_id"])
                st.session_state.pending_nav = (
                    "app_pages/window_detail.py" if f["target_type"] == "WINDOW" else "app_pages/dish_detail.py"
                )

        st.dataframe(
            fav_df,
            hide_index=True,
            column_config={"操作": st.column_config.ButtonColumn("操作", on_click=open_fav, key="fav_click")},
        )

with tab_submissions:
    wins = db.query(
        "SELECT id, name, status, created_at FROM food_window WHERE submitter_id = ? ORDER BY id DESC",
        (user["id"],),
    )
    dss = db.query(
        "SELECT id, name, status, created_at FROM dish WHERE submitter_id = ? ORDER BY id DESC",
        (user["id"],),
    )
    subs = [("档口", w) for w in wins] + [("菜品", d) for d in dss]
    if not subs:
        st.caption("暂无投稿")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "类型": kind,
                        "名称": item["name"],
                        "状态": "待审核" if item["status"] == "PENDING" else "已上架",
                        "提交时间": item["created_at"],
                    }
                    for kind, item in subs
                ]
            ),
            hide_index=True,
        )

sess.handle_nav()
