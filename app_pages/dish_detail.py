"""菜品详情：信息、统计、评分、点赞、收藏、评价列表。"""
import streamlit as st

from core import files
from core import session as sess
from services import dishes, interactions, ratings

sess.handle_nav()

target = st.session_state.get("detail_target")
if not target or target["type"] != "DISH":
    # 兜底：直接从 URL 查询参数恢复（例如分享链接或 page_link 跳转）
    q = st.query_params
    if q.get("type") == "DISH" and q.get("id"):
        try:
            target = {"type": "DISH", "id": int(q["id"])}
            st.session_state.detail_target = target
        except (ValueError, TypeError):
            target = None

if not target or target["type"] != "DISH":
    st.info("请先从榜单选择一个菜品")
    if st.button("回到榜单"):
        st.switch_page("app_pages/home.py")
    st.stop()

dish_id = target["id"]
view_key = f"DISH:{dish_id}"
if view_key not in st.session_state.viewed_targets:
    st.session_state.viewed_targets.add(view_key)
    dish = dishes.get_dish(dish_id, increment_view=True)
else:
    dish = dishes.get_dish(dish_id)

if not dish:
    st.error("菜品不存在或已下架")
    st.stop()

st.subheader(dish["name"])
st.caption(f"📍 {dish['canteen_name']} · {dish['window_name']}  ·  ¥{dish['price']:.2f}")
image = files.resolve_image(dish.get("image"))
if image:
    st.image(str(image), width=420)
if dish.get("description"):
    st.markdown(dish["description"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("综合分", dish["score_avg"], border=True)
c2.metric("评分数", dish["rating_count"], border=True)
c3.metric("点赞", dish["like_count"], border=True)
c4.metric("收藏", dish["favorite_count"], border=True)
c5.metric("浏览", dish["view_count"], border=True)
st.caption(f"口味 {dish['taste_avg']}  ·  性价比 {dish['value_avg']}  ·  分量 {dish['portion_avg']}")

user = sess.current_user()
if user:
    liked = interactions.is_liked(user["id"], "DISH", dish_id)
    favorited = interactions.is_favorited(user["id"], "DISH", dish_id)
    b1, b2 = st.columns(2)
    if b1.button("👍 已点赞" if liked else "👍 点赞", width="stretch"):
        interactions.toggle_like(user["id"], "DISH", dish_id)
        st.rerun()
    if b2.button("⭐ 已收藏" if favorited else "⭐ 收藏", width="stretch"):
        interactions.toggle_favorite(user["id"], "DISH", dish_id)
        st.rerun()
else:
    st.caption("登录后可点赞、收藏、评分")

st.subheader("评分")
if user:
    existing = ratings.user_rating(user["id"], "DISH", dish_id)
    with st.form("rating_form"):
        taste = st.slider("口味", 1, 5, existing["taste"] if existing else 3)
        value = st.slider("性价比", 1, 5, existing["value_score"] if existing else 3)
        portion = st.slider("分量", 1, 5, existing["portion"] if existing else 3)
        comment = st.text_area("评语", value=(existing["comment"] if existing else ""), placeholder="说说你的体验…")
        submitted = st.form_submit_button("更新评分" if existing else "提交评分", width="stretch")
    if submitted:
        ratings.upsert_rating(user["id"], "DISH", dish_id, taste, value, portion, comment)
        st.toast("评分已提交")
        st.rerun()
else:
    st.info("登录后即可评分")

st.subheader(f"全部评价（{dish['rating_count']}）")
for r in ratings.list_ratings("DISH", dish_id):
    with st.container(border=True):
        st.markdown(f"**{r['nickname']}**  ·  口味 {r['taste']} / 性价比 {r['value_score']} / 分量 {r['portion']}")
        if r["comment"]:
            st.markdown(r["comment"])
        st.caption(r["created_at"])
