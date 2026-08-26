# 桂航美食推荐排行榜（Streamlit 版）

参考 [guat-food-recommendations](https://github.com/king001gg/guat-food-recommendations)（Spring Boot 3 + Vue 3）用 **Python + Streamlit** 重写的单体应用。支持档口 + 菜品两级榜单、多维评分、点赞、收藏、投稿审核与后台管理，本地 `streamlit run app.py` 即可运行，无需安装数据库。

## 功能特性

- 🏆 两级排行榜：档口榜 + 菜品榜，支持按食堂、档口、关键词筛选
- 📊 四种榜单：综合榜 / 好评榜 / 人气榜 / 热门榜（近 30 天）
- ⭐ 三维评分（口味 / 性价比 / 分量）+ 评语，同一用户对同一目标仅保留一条（upsert）
- 👍 点赞 / ⭐ 收藏，同一用户对同一目标仅一次
- 📝 投稿审核：普通用户投稿进入「待审核」，管理员直接上架，审核后展示
- 🔐 登录 / 注册 + 角色权限（普通用户 / 管理员），后台入口仅管理员可见
- 🛠️ 管理后台：数据概览（ECharts 图表）+ 审核 + 档口 / 菜品 / 食堂 / 用户管理
- 🖼️ 图片上传：档口封面、菜品图片，本地 `uploads/` 目录
- 🚀 航天主题界面：深空星云背景、星空粒子、火箭横幅与页脚（对齐原项目前端）

## 技术栈

| 层 | 选型 |
|---|---|
| 框架 | Streamlit（多页面 + session_state） |
| 数据库 | SQLite（标准库 sqlite3，单文件 `data/guatfood.db`） |
| 图表 | ECharts（`st.iframe` + CDN，`core/charts.py`） |
| 密码 | bcrypt |
| 图片 | Pillow |
| 数据中间层 | pandas |

## 目录结构

```
├── app.py                 # 入口：多页面导航 + 登录态
├── core/                  # 数据层：db / auth / seed / algorithms / files / session
├── services/              # 业务层：rankings / windows / dishes / ratings / interactions / admin
└── app_pages/             # 页面：榜单 / 详情 / 登录注册 / 个人中心 / 投稿 / 后台
```

## 快速开始

```bash
pip install -r requirements.txt
streamlit run app.py
```

- 首次启动自动建表并写入种子数据（食堂 / 档口 / 菜品 / 评分 / 点赞 / 收藏）。
- 访问 http://localhost:8501

### 演示账号

管理员账号 `guihanxiaoxiaol` / 密码 `lds666666`；其余演示用户统一密码 `123456`（可分别用环境变量 `ADMIN_PASSWORD` / `DEMO_PASSWORD` 覆盖）：

| 账号 | 角色 |
|---|---|
| `guihanxiaoxiaol` | 管理员 |
| `zhangsan` / `lisi` / `wangwu` / `zhaoliu` / `sunqi` | 普通用户 |

## 排行榜算法

| 榜单 | 排序键 |
|---|---|
| 综合榜 | `scoreAvg = (口味 + 性价比 + 分量) ÷ 3`，同分按评分数 |
| 好评榜 | 口味均分，同分按评分数 |
| 人气榜 | `heat = 评分数×10 + 点赞数×5 + 浏览量` |
| 热门榜 | 近 30 天评分数 |

## 说明

- 数据库文件 `data/guatfood.db` 与上传图片 `uploads/` 均不入库（已加入 `.gitignore`），删除后重启即可重新生成。
- 与原项目相比，档口 / 菜品新增 `submitter_id` 字段用于「我的投稿」追溯（原项目未记录投稿人）。
- 登录态基于浏览器会话（session_state），适合本地单机使用；若需多用户远程部署，建议后续拆出 FastAPI 后端 + 对象存储。
