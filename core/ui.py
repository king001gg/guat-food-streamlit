"""航天主题 UI 组件：深空星云背景、星空、hero 横幅、页脚。

Streamlit 的 config.toml 只能设置主题色，无法表达「深空星云渐变 + 星空 + 火箭横幅」
这类视觉，因此这里通过注入一小段针对性 CSS 与自包含 HTML 组件实现。配色与结构
对齐原项目前端（frontend/src/assets/guat.css）。
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
/* ============ 深空星云背景 + 静态星空 ============ */
.stApp, [data-testid="stAppViewContainer"] {
  background-color: #0b1e3a;
  background-image:
    radial-gradient(1.2px 1.2px at 20% 30%, rgba(255, 255, 255, 0.65), transparent 60%),
    radial-gradient(1px 1px at 68% 18%, rgba(255, 255, 255, 0.5), transparent 60%),
    radial-gradient(1.3px 1.3px at 44% 64%, rgba(255, 255, 255, 0.55), transparent 60%),
    radial-gradient(1px 1px at 84% 42%, rgba(255, 255, 255, 0.45), transparent 60%),
    radial-gradient(1.1px 1.1px at 8% 82%, rgba(255, 255, 255, 0.5), transparent 60%),
    radial-gradient(1100px 620px at 88% -12%, rgba(77, 163, 255, 0.18), transparent 60%),
    radial-gradient(900px 540px at -6% 16%, rgba(19, 58, 111, 0.45), transparent 55%),
    radial-gradient(760px 500px at 50% 118%, rgba(11, 30, 58, 0.55), transparent 60%),
    linear-gradient(165deg, #0a1a33 0%, #0b1e3a 42%, #133a6f 100%);
  background-size:
    260px 260px, 320px 320px, 300px 300px, 340px 340px, 280px 280px,
    auto, auto, auto, auto;
  background-repeat: repeat, repeat, repeat, repeat, repeat, no-repeat, no-repeat, no-repeat, no-repeat;
  background-attachment: fixed;
}

/* ============ Hero 横幅 · 深空 + 星轨 + 火箭 ============ */
.guat-hero {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 46px 36px;
  margin: 0 0 24px;
  color: #fff;
  background:
    radial-gradient(420px 420px at 18% 8%, rgba(255, 255, 255, 0.16), transparent 62%),
    radial-gradient(360px 360px at 92% 100%, rgba(77, 163, 255, 0.35), transparent 60%),
    linear-gradient(120deg, #0b1e3a 0%, #133a6f 45%, #1e5aa8 100%);
  box-shadow: 0 14px 40px rgba(11, 30, 58, 0.32);
}
.guat-hero::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent);
}
.hero-stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1.6px 1.6px at 12% 22%, rgba(255, 255, 255, 0.95), transparent 60%),
    radial-gradient(1.1px 1.1px at 32% 58%, rgba(255, 255, 255, 0.7), transparent 60%),
    radial-gradient(1.6px 1.6px at 55% 24%, rgba(255, 255, 255, 0.85), transparent 60%),
    radial-gradient(1px 1px at 74% 62%, rgba(255, 255, 255, 0.6), transparent 60%),
    radial-gradient(1.6px 1.6px at 90% 30%, rgba(255, 255, 255, 0.9), transparent 60%),
    radial-gradient(1px 1px at 46% 80%, rgba(255, 255, 255, 0.5), transparent 60%),
    radial-gradient(1.2px 1.2px at 66% 12%, rgba(255, 255, 255, 0.75), transparent 60%);
  background-size: 340px 340px;
  animation: guat-twinkle 5.5s ease-in-out infinite;
  pointer-events: none;
}
.hero-orbit {
  position: absolute;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  pointer-events: none;
}
.hero-orbit-1 { width: 300px; height: 300px; right: -70px; top: -90px; }
.hero-orbit-2 { width: 440px; height: 440px; right: -140px; top: -160px; }
.hero-orbit-3 { width: 150px; height: 150px; left: -46px; bottom: -60px; }
.hero-rocket {
  position: absolute;
  right: 52px;
  top: 46%;
  transform: translateY(-50%);
  font-size: 62px;
  line-height: 1;
  animation: guat-float 4s ease-in-out infinite;
  filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.35));
}
.guat-hero h1 {
  position: relative;
  z-index: 1;
  margin: 0 0 10px;
  font-size: 32px;
  letter-spacing: 2px;
  font-weight: 800;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}
.guat-hero p {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: 14px;
  opacity: 0.92;
  max-width: 560px;
}
.hero-chips {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.hero-chips .chip {
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.13);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(6px);
  color: #fff;
  font-size: 13px;
}

/* ============ 页脚 ============ */
.guat-footer {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #08172e, #133a6f);
  color: #b9c7dd;
  border-radius: 14px;
  padding: 32px 16px 24px;
  margin-top: 32px;
}
.footer-stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1.4px 1.4px at 18% 30%, rgba(255, 255, 255, 0.8), transparent 60%),
    radial-gradient(1px 1px at 70% 20%, rgba(255, 255, 255, 0.6), transparent 60%),
    radial-gradient(1.4px 1.4px at 85% 60%, rgba(255, 255, 255, 0.7), transparent 60%),
    radial-gradient(1px 1px at 40% 70%, rgba(255, 255, 255, 0.5), transparent 60%);
  background-size: 260px 260px;
  animation: guat-twinkle 6s ease-in-out infinite;
  pointer-events: none;
}
.footer-inner {
  position: relative;
  max-width: 1100px;
  margin: 0 auto;
  text-align: center;
}
.footer-rocket { font-size: 26px; margin-bottom: 8px; }
.guat-footer p { margin: 3px 0; font-size: 13px; }
.guat-footer .brand { font-size: 15px; font-weight: 700; color: #fff; }
.guat-footer .sub { opacity: 0.75; }
.guat-footer .note { opacity: 0.5; font-size: 12px; }

/* ============ 榜单卡片（白卡浮于深空） ============ */
.guat-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(19, 58, 111, 0.16);
  margin-bottom: 10px;
  overflow: hidden;
}
.rank-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  color: #303133;
}
.rank-badge {
  flex-shrink: 0;
  width: 42px; height: 42px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800; color: #fff;
  background: #3b5a8f;
  position: relative;
}
.rank-badge.top1 { background: linear-gradient(135deg, #ff6b6b, #e74c3c); box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4); }
.rank-badge.top2 { background: linear-gradient(135deg, #ffb347, #f39c12); box-shadow: 0 4px 12px rgba(243, 156, 18, 0.36); }
.rank-badge.top3 { background: linear-gradient(135deg, #ffd26f, #f6b93b); box-shadow: 0 4px 12px rgba(246, 185, 59, 0.34); }
.rank-badge .crown {
  position: absolute; top: -9px; left: 50%;
  transform: translateX(-50%);
  font-size: 13px; line-height: 1;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.25));
}
.rank-thumb {
  flex-shrink: 0;
  width: 92px; height: 92px;
  border-radius: 12px; overflow: hidden;
  background: linear-gradient(135deg, #133a6f, #1e5aa8);
  display: flex; align-items: center; justify-content: center;
  color: #9ecbff; font-size: 34px;
}
.rank-thumb img { width: 100%; height: 100%; object-fit: cover; }
.rank-body { flex: 1; min-width: 0; }
.rank-title {
  font-size: 17px; font-weight: 600; color: #303133;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.rank-desc {
  margin: 6px 0; font-size: 13px; color: #909399;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rank-meta { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.score-text { color: #ff9f43; font-weight: 700; font-size: 18px; }
.meta-chip { font-size: 12px; color: #606266; display: inline-flex; align-items: center; gap: 4px; }
.rank-price {
  padding: 1px 8px; border-radius: 20px;
  border: 1px solid #ffd39b; color: #e67e22;
  font-size: 12px; font-weight: 600; background: #fff7e8;
}

/* ============ 动画 ============ */
@keyframes guat-twinkle {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}
@keyframes guat-float {
  0%, 100% { transform: translateY(-50%) translateY(0); }
  50% { transform: translateY(-50%) translateY(-12px); }
}
</style>
"""

_HERO = """
<div class="guat-hero">
  <div class="hero-stars"></div>
  <div class="hero-orbit hero-orbit-1"></div>
  <div class="hero-orbit hero-orbit-2"></div>
  <div class="hero-orbit hero-orbit-3"></div>
  <div class="hero-rocket">🚀</div>
  <h1>桂航美食推荐排行榜</h1>
  <p>桂林航天工业学院 · 最受同学们欢迎的食堂档口与菜品榜单</p>
  <div class="hero-chips">
    <span class="chip">🏆 多维评分</span>
    <span class="chip">🌟 真实评价</span>
    <span class="chip">🛰️ 桂航专属</span>
  </div>
</div>
"""

_FOOTER = """
<footer class="guat-footer">
  <div class="footer-stars"></div>
  <div class="footer-inner">
    <div class="footer-rocket">🚀</div>
    <p class="brand">桂航美食推荐排行榜</p>
    <p class="sub">桂林航天工业学院校园美食 · 数据来源于同学们的真实评价</p>
    <p class="sub note">仅代表个人口味观点 · 探索星辰，也探索食堂</p>
  </div>
</footer>
"""


def inject_theme() -> None:
    """注入航天主题 CSS（幂等，可在每次 rerun 调用）。"""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero() -> None:
    """首页顶部航天横幅。"""
    st.markdown(_HERO, unsafe_allow_html=True)


def footer() -> None:
    """全局页脚。"""
    st.markdown(_FOOTER, unsafe_allow_html=True)
