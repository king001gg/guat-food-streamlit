"""ECharts 图表封装。

Streamlit 1.60 不再兼容老旧的 ``streamlit-echarts`` 组件（其 file-backed JS 声明方式
已被禁止），因此这里改用 ``st.iframe`` 内嵌一段自包含 HTML，通过 CDN 加载 ECharts 渲染。
图表本身是静态 SVG/Canvas，页面侧的筛选、跳转等交互仍由 Streamlit 原生控件完成。

注意：图表渲染依赖联网加载 ECharts（jsDelivr CDN）。
"""
from __future__ import annotations

import json

import streamlit as st

ACCENT = "#4da3ff"  # 航天主题 sky 蓝
PALETTE = [
    "#4da3ff", "#ff9f43", "#f6b93b", "#3ddc97", "#e74c3c",
    "#9ecbff", "#8b5cf6", "#14b8a6",
]
TEXT_COLOR = "#e6eefb"  # 深空底上的浅色文字
AXIS_LINE = "#33507f"
SPLIT_LINE = "rgba(255, 255, 255, 0.06)"
_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"


def _render(option: dict, height: int) -> None:
    """把 ECharts option 渲染进 iframe。"""
    payload = json.dumps(option, ensure_ascii=False).replace("</", "<\\/")
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;'>"
        f"<div id='chart' style='width:100%;height:{height}px;'></div>"
        f"<script src='{_CDN}'></script>"
        "<script>"
        "const el=document.getElementById('chart');"
        "if(window.echarts){const c=echarts.init(el);c.setOption(" + payload + ");"
        "window.addEventListener('resize',()=>c.resize());}"
        "else{el.innerHTML='<p style=\"padding:12px;color:#999;\">图表加载失败（需联网加载 ECharts）</p>';}"
        "</script></body></html>"
    )
    st.iframe(html, height=height)


def _grid(top: int = 36, right: int = 24) -> dict:
    return {"left": 8, "right": right, "bottom": 4, "top": top, "containLabel": True}


def hbar(categories: list, values: list, title: str = "", height: int = 360) -> None:
    """横向柱状图（适合排行榜），自动升序后让第一名在最上。"""
    pairs = sorted(zip(categories, values), key=lambda kv: kv[1])
    option = {
        "title": {"text": title, "left": 0, "top": 0, "textStyle": {"fontSize": 14, "color": TEXT_COLOR}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": _grid(),
        "xAxis": {"type": "value", "axisLine": {"lineStyle": {"color": AXIS_LINE}}, "splitLine": {"lineStyle": {"color": SPLIT_LINE}}},
        "yAxis": {
            "type": "category",
            "data": [p[0] for p in pairs],
            "inverse": True,
            "axisLine": {"lineStyle": {"color": AXIS_LINE}},
            "axisLabel": {"color": TEXT_COLOR, "width": 120, "overflow": "truncate"},
        },
        "series": [
            {
                "type": "bar",
                "data": [p[1] for p in pairs],
                "barMaxWidth": 22,
                "itemStyle": {"color": ACCENT, "borderRadius": [0, 6, 6, 0]},
                "label": {"show": True, "position": "right", "color": TEXT_COLOR},
            }
        ],
    }
    _render(option, height)


def vbar(categories: list, values: list, title: str = "", height: int = 320) -> None:
    """纵向柱状图（适合分布）。"""
    option = {
        "title": {"text": title, "left": 0, "top": 0, "textStyle": {"fontSize": 14, "color": TEXT_COLOR}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": _grid(),
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLine": {"lineStyle": {"color": AXIS_LINE}},
            "axisLabel": {"color": TEXT_COLOR, "interval": 0},
        },
        "yAxis": {"type": "value", "axisLine": {"lineStyle": {"color": AXIS_LINE}}, "splitLine": {"lineStyle": {"color": SPLIT_LINE}}},
        "series": [
            {
                "type": "bar",
                "data": values,
                "barMaxWidth": 36,
                "itemStyle": {"color": ACCENT, "borderRadius": [6, 6, 0, 0]},
                "label": {"show": True, "position": "top", "color": TEXT_COLOR},
            }
        ],
    }
    _render(option, height)


def grouped(categories: list, series: list[dict], title: str = "", height: int = 320) -> None:
    """分组纵向柱状图。series 形如 [{"name": "档口", "data": [...]}, ...]。"""
    option = {
        "title": {"text": title, "left": 0, "top": 0, "textStyle": {"fontSize": 14, "color": TEXT_COLOR}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 0, "right": 0, "textStyle": {"color": TEXT_COLOR}},
        "grid": _grid(top=48),
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLine": {"lineStyle": {"color": AXIS_LINE}},
            "axisLabel": {"color": TEXT_COLOR, "interval": 0},
        },
        "yAxis": {"type": "value", "axisLine": {"lineStyle": {"color": AXIS_LINE}}, "splitLine": {"lineStyle": {"color": SPLIT_LINE}}},
        "series": [
            {
                "name": s["name"],
                "type": "bar",
                "data": s["data"],
                "barMaxWidth": 22,
                "itemStyle": {"color": PALETTE[i % len(PALETTE)], "borderRadius": [4, 4, 0, 0]},
            }
            for i, s in enumerate(series)
        ],
    }
    _render(option, height)
