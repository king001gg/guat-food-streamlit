"""后台管理：概览、审核、档口/菜品/食堂/用户管理（仅管理员）。"""
import pandas as pd
import streamlit as st

from core import charts
from core import session as sess
from services import admin as admin_svc
from services import dishes, windows

if not sess.is_admin():
    st.error("无权访问后台管理")
    st.stop()

tab_overview, tab_review, tab_windows, tab_dishes, tab_canteens, tab_users = st.tabs(
    ["概览", "审核", "档口管理", "菜品管理", "食堂管理", "用户管理"]
)

with tab_overview:
    o = admin_svc.overview()
    with st.container(horizontal=True):
        st.metric("用户", o["users"], border=True)
        st.metric("食堂", o["canteens"], border=True)
        st.metric("档口", o["windows"], border=True)
        st.metric("菜品", o["dishes"], border=True)
        st.metric("评分", o["ratings"], border=True)
        st.metric("待审核", o["pending_windows"] + o["pending_dishes"], border=True)

    col1, col2 = st.columns(2)
    with col1:
        charts.grouped(
            [c["name"] for c in o["canteen_stats"]],
            [
                {"name": "档口", "data": [c["window_count"] for c in o["canteen_stats"]]},
                {"name": "菜品", "data": [c["dish_count"] for c in o["canteen_stats"]]},
            ],
            title="各食堂档口 / 菜品数",
        )
    with col2:
        dist = sorted(o["rating_dist"], key=lambda d: d["taste"])
        charts.vbar([str(d["taste"]) for d in dist], [d["c"] for d in dist], title="口味评分分布")

    col3, col4 = st.columns(2)
    with col3:
        charts.hbar([r["name"] for r in o["top_windows"]], [r["heat"] for r in o["top_windows"]], title="人气档口 Top 10")
    with col4:
        charts.hbar([r["name"] for r in o["top_dishes"]], [r["heat"] for r in o["top_dishes"]], title="人气菜品 Top 10")

with tab_review:
    st.subheader("待审核档口")
    pw = windows.pending()
    if not pw:
        st.caption("无待审核档口")
    for w in pw:
        with st.container(border=True):
            st.markdown(f"**{w['name']}**  ·  {w['canteen_name']} · {w['location'] or ''}")
            if w["description"]:
                st.markdown(w["description"])
            c1, c2 = st.columns(2)
            if c1.button("✅ 通过", key=f"pw_{w['id']}"):
                windows.set_status(w["id"], "PUBLISHED")
                st.rerun()
            if c2.button("❌ 驳回", key=f"rw_{w['id']}"):
                windows.delete(w["id"])
                st.rerun()

    st.subheader("待审核菜品")
    pd_rows = dishes.pending()
    if not pd_rows:
        st.caption("无待审核菜品")
    for d in pd_rows:
        with st.container(border=True):
            st.markdown(f"**{d['name']}**  ·  {d['canteen_name']} / {d['window_name']}  ·  ¥{d['price']:.2f}")
            if d["description"]:
                st.markdown(d["description"])
            c1, c2 = st.columns(2)
            if c1.button("✅ 通过", key=f"pd_{d['id']}"):
                dishes.set_status(d["id"], "PUBLISHED")
                st.rerun()
            if c2.button("❌ 驳回", key=f"rd_{d['id']}"):
                dishes.delete(d["id"])
                st.rerun()

with tab_windows:
    rows = windows.list_admin()
    df = pd.DataFrame(
        [
            {
                "ID": w["id"],
                "名称": w["name"],
                "食堂": w["canteen_name"],
                "状态": "待审核" if w["status"] == "PENDING" else "已上架",
                "浏览": w["view_count"],
                "操作": "删除",
            }
            for w in rows
        ]
    )

    def del_win():
        click = st.session_state.get("del_win_click")
        if click and click.get("row") is not None:
            windows.delete(rows[click["row"]]["id"])

    st.dataframe(
        df,
        hide_index=True,
        column_config={"操作": st.column_config.ButtonColumn("操作", on_click=del_win, key="del_win_click")},
    )

with tab_dishes:
    rows = dishes.list_admin()
    df = pd.DataFrame(
        [
            {
                "ID": d["id"],
                "名称": d["name"],
                "食堂": d["canteen_name"],
                "档口": d["window_name"],
                "价格": d["price"],
                "状态": "待审核" if d["status"] == "PENDING" else "已上架",
                "操作": "删除",
            }
            for d in rows
        ]
    )

    def del_dish():
        click = st.session_state.get("del_dish_click")
        if click and click.get("row") is not None:
            dishes.delete(rows[click["row"]]["id"])
            st.rerun()

    st.caption("直接改「名称 / 价格」单元格，改完点下方「保存修改」")
    edited = st.data_editor(
        df,
        hide_index=True,
        num_rows="fixed",
        disabled=["ID", "食堂", "档口", "状态"],
        column_config={
            "名称": st.column_config.TextColumn("名称"),
            "价格": st.column_config.NumberColumn("价格", format="¥%.2f"),
            "操作": st.column_config.ButtonColumn("操作", on_click=del_dish, key="del_dish_click"),
        },
        key="dish_editor",
    )

    if st.button("保存修改", width="stretch"):
        changed = 0
        for i, r in enumerate(edited.to_dict("records")):
            if i >= len(rows):
                break
            orig = rows[i]
            new_name = str(r.get("名称") or "").strip()
            try:
                new_price = float(r.get("价格"))
            except (TypeError, ValueError):
                new_price = orig["price"]
            if not new_name:
                st.error(f"第 {i + 1} 行名称为空，跳过")
                continue
            if new_name != orig["name"] or new_price != orig["price"]:
                dishes.update(orig["id"], new_name, orig["description"], new_price)
                changed += 1
        if changed:
            st.toast(f"已保存 {changed} 处修改")
            st.rerun()
        else:
            st.info("没有改动")

with tab_canteens:
    with st.form("add_canteen"):
        name = st.text_input("名称")
        location = st.text_input("位置")
        sort_order = st.number_input("排序", min_value=0, value=0, step=1)
        add = st.form_submit_button("添加食堂", width="stretch")
    if add:
        if not name.strip():
            st.error("请填写名称")
        else:
            try:
                admin_svc.create_canteen(name.strip(), location.strip(), sort_order)
                st.toast("已添加")
                st.rerun()
            except Exception:
                st.error("名称已存在")

    st.caption("删除食堂会同时删除其下所有档口与菜品")
    rows = admin_svc.list_canteens()
    df = pd.DataFrame(
        [{"ID": c["id"], "名称": c["name"], "位置": c["location"], "排序": c["sort_order"], "操作": "删除"} for c in rows]
    )

    def del_canteen():
        click = st.session_state.get("del_canteen_click")
        if click and click.get("row") is not None:
            admin_svc.delete_canteen(rows[click["row"]]["id"])

    st.dataframe(
        df,
        hide_index=True,
        column_config={"操作": st.column_config.ButtonColumn("操作", on_click=del_canteen, key="del_canteen_click")},
    )

with tab_users:
    rows = admin_svc.list_users()
    df = pd.DataFrame(
        [
            {
                "ID": u["id"],
                "用户名": u["username"],
                "昵称": u["nickname"],
                "角色": "管理员" if u["role"] == "ADMIN" else "用户",
                "状态": "正常" if u["status"] == "ACTIVE" else "禁用",
                "操作": "禁用" if u["status"] == "ACTIVE" else "启用",
                "删除": "删除",
            }
            for u in rows
        ]
    )

    def toggle_user():
        click = st.session_state.get("toggle_user_click")
        if click and click.get("row") is not None:
            u = rows[click["row"]]
            admin_svc.set_user_status(u["id"], "DISABLED" if u["status"] == "ACTIVE" else "ACTIVE")

    def del_user():
        click = st.session_state.get("del_user_click")
        if click and click.get("row") is not None:
            u = rows[click["row"]]
            if u["role"] == "ADMIN":
                st.toast("不能删除管理员账号")
            else:
                admin_svc.delete_user(u["id"])

    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "操作": st.column_config.ButtonColumn("操作", on_click=toggle_user, key="toggle_user_click"),
            "删除": st.column_config.ButtonColumn("删除", on_click=del_user, key="del_user_click"),
        },
    )
