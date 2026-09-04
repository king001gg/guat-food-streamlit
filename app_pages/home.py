"""榜单首页：菜品 / 档口两级榜单，4 种维度，筛选 + 搜索 + 可视化。"""
import streamlit as st

from core import charts, files, ui
from core import db
from core import session as sess
from core.algorithms import RANK_LABELS
from services import dishes, rankings, windows

sess.handle_nav()
ui.hero()

TARGET_LABELS = {"WINDOW": "档口", "DISH": "菜品"}
METRIC = {"overall": "score_avg", "taste": "taste_avg", "heat": "heat", "recent": "recent_count"}

target_type = st.segmented_control(
    "榜单类型",
    ["DISH", "WINDOW"],
    format_func=lambda v: TARGET_LABELS[v],
    default="DISH",
)
rank_type = st.segmented_control(
    "榜单维度",
    ["overall", "taste", "heat", "recent"],
    format_func=lambda v: RANK_LABELS[v],
    default="overall",
)

canteens = db.query("SELECT id, name FROM canteen ORDER BY sort_order, id")

col1, col2 = st.columns(2)
with col1:
    canteen_choice = st.selectbox(
        "食堂", ["全部"] + [c["name"] for c in canteens], key="home_canteen"
    )
with col2:
    keyword = st.text_input("关键词搜索", key="home_keyword", placeholder="输入名称或描述")

canteen_id = None
if canteen_choice != "全部":
    canteen_id = next(c["id"] for c in canteens if c["name"] == canteen_choice)

window_id = None
if target_type == "DISH":
    win_list = windows.list_published(canteen_id)
    win_choice = st.selectbox("档口", ["全部"] + [w["name"] for w in win_list], key="home_window")
    if win_choice != "全部":
        window_id = next(w["id"] for w in win_list if w["name"] == win_choice)

rows = rankings.get_rankings(
    target_type,
    rank_type,
    canteen_id=canteen_id,
    window_id=window_id,
    keyword=keyword,
)

if not rows:
    st.info("暂无数据，换个筛选条件试试")
    st.stop()

# 可视化：Top 10 横向柱状图
metric = METRIC[rank_type]
top = rows[:10]
charts.hbar(
    [r["name"] for r in top],
    [round(r[metric], 2) if isinstance(r[metric], float) else r[metric] for r in top],
    title=f"{RANK_LABELS[rank_type]} Top 10",
)

# 榜单卡片列表（对齐原项目 RankItem：名次徽章 + 缩略图 + 评分 + 元信息）
def _badge_class(rank: int) -> str:
    return {1: "top1", 2: "top2", 3: "top3"}.get(rank, "")


def _rank_card(r: dict, rank: int) -> str:
    cls = _badge_class(rank)
    crown = '<span class="crown">👑</span>' if rank == 1 else ""
    img = files.image_data_uri(r.get("cover_image") or r.get("image"))
    thumb = f'<img src="{img}" alt="{r["name"]}"/>' if img else ("🏪" if target_type == "WINDOW" else "🍜")
    if target_type == "WINDOW":
        location = f'{r.get("canteen_name") or ""} · {r.get("location") or "未知位置"}'
        price_tag = ""
    else:
        location = r.get("window_name") or ""
        price_tag = f'<span class="rank-price">¥{r.get("price", 0):.2f}</span>'
    desc = (r.get("description") or "暂无简介").strip() or "暂无简介"
    return f"""
<div class="guat-card rank-item">
  <div class="rank-badge {cls}">{crown}{rank}</div>
  <div class="rank-thumb">{thumb}</div>
  <div class="rank-body">
    <div class="rank-title">{r["name"]}{price_tag}</div>
    <div class="rank-desc">{desc}</div>
    <div class="rank-meta">
      <span class="score-text">{r["score_avg"]:.1f}</span>
      <span class="meta-chip">⭐ 综合评分</span>
      <span class="meta-chip">💬 {r["rating_count"]} 条评价</span>
      <span class="meta-chip">👁 {r["view_count"]} 浏览</span>
      <span class="meta-chip">📍 {location}</span>
    </div>
  </div>
</div>"""


detail_page = "app_pages/window_detail.py" if target_type == "WINDOW" else "app_pages/dish_detail.py"
for i, r in enumerate(rows, 1):
    st.markdown(_rank_card(r, i), unsafe_allow_html=True)
    if st.button("查看详情 →", key=f"detail_{target_type}_{r['id']}", width="stretch"):
        sess.set_detail_target(target_type, r["id"])
        st.session_state.pending_nav = detail_page

sess.handle_nav()
