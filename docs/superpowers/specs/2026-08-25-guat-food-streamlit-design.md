# 桂航美食推荐排行榜（Streamlit 版）设计文档

- 日期：2026-08-25
- 状态：已确认（待进入实现计划）
- 参考项目：[king001gg/guat-food-recommendations](https://github.com/king001gg/guat-food-recommendations)

## 1. 背景与目标

参考已有的「桂航美食推荐排行榜」全栈项目（Spring Boot 3 + Vue 3），用 **Python + Streamlit** 重写一个功能对等的单体应用。目标：

- 在单个 Streamlit 应用内完整复刻核心功能：两级榜单、多维评分、点赞/收藏、投稿审核、管理员后台、登录与角色权限、图片上传。
- 本地 `streamlit run app.py` 即可运行，无需额外安装数据库。
- 代码结构清晰、易维护，便于后续扩展。

## 2. 范围

### 包含（完整移植）
- 两级榜单：档口榜 + 菜品榜
- 4 种榜单：综合榜 / 好评榜 / 人气榜 / 热门榜（近 30 天）
- 三维评分（口味 / 性价比 / 分量）+ 评语，同一用户对同一目标仅一条评分（upsert）
- 点赞、收藏（同一用户对同一目标仅一次）
- 投稿审核：普通用户投稿 → 待审核；管理员审核后上架
- 管理员后台：概览图表 + 档口 / 菜品 / 食堂 / 评分 / 用户管理（CRUD + 审核）
- 登录 / 注册，角色区分（USER / ADMIN）
- 图片上传（档口封面、菜品图片）

### 不包含（YAGNI）
- 真实 JWT / 多端 REST API（Streamlit 单体用 session 登录替代）
- 邮箱验证、找回密码、第三方登录
- 评论回复、举报、黑名单
- MySQL 部署、HTTPS / systemd 部署脚本（本期仅本地运行）

## 3. 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 框架 | Streamlit | 多页面 + `session_state` 状态管理 |
| 数据库 | SQLite（标准库 `sqlite3`） | 单文件 `data/guatfood.db`，裸 SQL，不引 ORM |
| 图表 | Plotly | 榜单柱状图、后台概览 |
| 密码 | bcrypt | 哈希入库 |
| 图片 | Pillow | 上传压缩，存本地 `uploads/` |
| 数据中间层 | pandas | 榜单 / 统计聚合 |

## 4. 架构与目录结构

```
guat delicious/
├── app.py                 # 入口：多页面导航 + 登录态展示
├── requirements.txt
├── README.md
├── .gitignore
├── data/guatfood.db       # 首次运行自动生成（不提交）
├── uploads/               # 上传图片（不提交）
├── core/
│   ├── db.py              # 连接（sqlite3）+ 建表 DDL + 通用查询助手
│   ├── auth.py            # 注册 / 登录 / 当前用户 / 角色校验
│   ├── seed.py            # 首次启动写入种子数据
│   └── algorithms.py      # 4 种榜单算法（纯函数）
├── services/
│   ├── windows.py         # 档口查询 / 详情 / 投稿 / 审核
│   ├── dishes.py          # 菜品查询 / 详情 / 投稿 / 审核
│   ├── ratings.py         # 评分 upsert / 评分列表 / 聚合
│   ├── interactions.py    # 点赞 / 收藏（toggle）
│   └── admin.py           # 后台统计 / CRUD
└── pages/
    ├── 1_🏠_榜单首页.py
    ├── 2_🍜_档口详情.py
    ├── 3_🍚_菜品详情.py
    ├── 4_🔐_登录注册.py
    ├── 5_👤_个人中心.py
    ├── 6_📝_投稿.py
    └── 7_🛠️_后台管理.py
```

**设计原则**：每个模块职责单一、可独立理解与测试。`core/` 是数据与规则层（无 UI），`services/` 是业务逻辑层，`pages/` 是 UI 层。业务逻辑不写在页面里。

## 5. 数据模型（7 张表，字段沿用原项目）

> SQLite 方言。表名沿用原项目规避保留字：档口用 `food_window`、性价比列用 `value_score`。

- `user`：id, username(唯一), password(哈希), nickname, avatar, role(USER/ADMIN), status(ACTIVE/DISABLED), created_at, updated_at
- `canteen`：id, name(唯一), location, sort_order, created_at, updated_at
- `food_window`：id, canteen_id, name, description, cover_image, location, status(PUBLISHED/PENDING), view_count, created_at, updated_at
- `dish`：id, window_id, name, description, image, price, status(PUBLISHED/PENDING), view_count, created_at, updated_at
- `rating`：id, user_id, target_type(WINDOW/DISH), target_id, taste(1-5), value_score(1-5), portion(1-5), comment, created_at；唯一约束 `(user_id, target_type, target_id)`
- `like_record`：id, user_id, target_type, target_id, created_at；唯一约束 `(user_id, target_type, target_id)`
- `favorite`：id, user_id, target_type, target_id, created_at；唯一约束 `(user_id, target_type, target_id)`

外键关系用索引代替；`rating/like_record/favorite` 的 `target_type` 用 `WINDOW` / `DISH` 区分两级目标。

## 6. 页面与交互

1. **榜单首页**：档口 / 菜品两个 tab；每个 tab 内 4 种榜单子 tab（综合/好评/人气/热门）；食堂筛选（下拉）、关键词搜索（文本框）；Plotly 柱状图 + 榜单表格；点击某行进入详情页。
2. **档口详情 / 菜品详情**：通过 `session_state` 传递目标 id 进入；展示信息、图片、三维均分、评分数、点赞数、浏览量；评分表单（三维星级 + 评语）；点赞 / 收藏按钮；评分列表。
3. **登录 / 注册**：表单提交；成功后写入 `session_state.user`，跳转榜单首页。
4. **个人中心**：我的评分、我的收藏、我的投稿、修改昵称/头像。
5. **投稿**：普通用户投稿档口/菜品（含图片上传），默认 `PENDING`；管理员投稿直接 `PUBLISHED`。
6. **后台管理**（仅管理员可见，侧边栏对非管理员隐藏入口）：数据概览（Plotly：评分分布、各食堂档口/菜品数、人气 Top）；档口/菜品/食堂/评分/用户 CRUD；待审核列表 + 通过/驳回。

**状态管理**：`session_state.user`（当前登录用户）、`session_state.detail_target`（详情页目标）、`session_state.active_rank`（当前榜单 tab）等。

## 7. 排行榜算法（沿用原项目）

| 榜单 | 排序键 | 备注 |
|---|---|---|
| 综合榜 | `scoreAvg = (taste + value_score + portion) / 3` | 同分按评分数降序 |
| 好评榜 | `tasteAvg` | 同分按评分数降序 |
| 人气榜 | `heat = 评分数×10 + 点赞数×5 + 浏览量` | |
| 热门榜 | 近 30 天评分数 `recentCount` | |

算法实现为 `core/algorithms.py` 中的纯函数，输入 DataFrame 输出排序结果，便于单独测试。

## 8. 登录与权限

- 密码 bcrypt 哈希后入库，登录时校验。
- `session_state.user` 保存 `{id, username, nickname, role}`。
- 角色：`USER` / `ADMIN`；后台页面对非管理员隐藏入口，且页面内再次校验。
- 未登录访问点赞/收藏/评分时，引导跳转登录页。

## 9. 图片处理

- 用 `st.file_uploader` 上传，Pillow 压缩（限制最长边、转 RGB）后存 `uploads/`，文件名用时间戳/uuid，路径入库。
- 无图时用占位（emoji + 背景色块）。
- `uploads/` 与 `data/` 加入 `.gitignore`。

## 10. 种子数据（复用原项目）

首次启动（`user` 表为空）时自动写入：

- 用户：`guihanxiaoxiaol`（ADMIN）+ `zhangsan`/`lisi`/`wangwu`/`zhaoliu`/`sunqi`（USER）
- 食堂：天舟楼食堂（南校区）、天宫楼食堂（北校区）、莘子苑食堂（东校区）、校外（商业街）
- 档口：桂林米粉、柳州螺蛳粉、自选快餐、麻辣香锅、黄焖鸡米饭、兰州拉面、烤肉拌饭、石锅拌饭、港式烧腊、糖水铺
- 菜品：桂林米粉、卤菜粉、招牌螺蛳粉、干捞螺蛳粉、两荤一素套餐、麻辣香锅(自选)、黄焖鸡米饭、牛肉拉面、蜜汁烤肉饭、五花肉石锅拌饭、叉烧饭、杨枝甘露
- 评分/点赞/收藏：演示用户对档口/菜品的示例数据（评分含三维 + 评语）

## 11. 关键默认决策（已确认）

1. 种子密码**不写入仓库**，通过环境变量 `ADMIN_PASSWORD` / `DEMO_PASSWORD` 或 `.streamlit/secrets.toml` 配置（本地演示可自行固定）。
2. 图片存本地 `uploads/`，路径入库。
3. 数据库用**裸 `sqlite3` + SQL**，不引 ORM。

## 12. 错误处理

- 数据库操作统一 try/except，出错用 `st.error` 提示用户，不抛堆栈到页面。
- 登录失败、重复用户名、非法输入等在表单层校验并给出中文提示。
- 越权操作（非管理员访问后台、未登录点赞）在 UI 层拦截 + 业务层再次校验。

## 13. 验证方式

- 手动运行 `streamlit run app.py`，按功能走查：注册/登录、浏览榜单、评分/点赞/收藏、投稿→审核→上架、后台 CRUD。
- 核心算法与评分 upsert 逻辑用独立脚本/断言做最小验证。

## 14. 部署

- 本地：`pip install -r requirements.txt && streamlit run app.py`。
- 本期不做云部署；SQLite 与本地 `uploads/` 不适用于多实例云环境，若后续上云需换对象存储 + 托管数据库（留作扩展）。

## 15. 后续扩展（本期不做）

- 图表库换 ECharts（`streamlit-echarts`），样式更接近原项目。
- 云部署：Streamlit Community Cloud / 自托管 + 对象存储。
- 真实会话/多端 API：拆出 FastAPI 后端。
