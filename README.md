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
- 🖼️ 图片上传：档口封面、菜品图片，优先 Supabase Storage（配置 anon key），回退本地 `uploads/` 目录
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

管理员账号 `guihanxiaoxiaol`；其余演示用户 `zhangsan` / `lisi` / `wangwu` / `zhaoliu` / `sunqi` 共用一个密码。密码**不写入仓库**，通过环境变量或 `.streamlit/secrets.toml` 配置（见下方「密码配置」）：

| 账号 | 角色 |
|---|---|
| `guihanxiaoxiaol` | 管理员 |
| `zhangsan` / `lisi` / `wangwu` / `zhaoliu` / `sunqi` | 普通用户 |

### 配置

应用从 Streamlit Secrets（本地 `.streamlit/secrets.toml` / Streamlit Cloud 的 Secrets）或环境变量读取以下配置：

```toml
# 种子账号密码（不写入仓库）
ADMIN_PASSWORD = "你的管理员密码"
DEMO_PASSWORD = "你的演示用户密码"

# 可选：托管 PostgreSQL 连接串。配置后改用 PostgreSQL 持久化；不配置则用本地 SQLite。
DATABASE_URL = "postgresql://user:password@host:5432/dbname"

# 可选：Supabase 匿名 key。配置后上传图片写入对象存储（线上持久、可显示）；不配置则存本地 uploads/。
SUPABASE_ANON_KEY = "eyJ...anon key..."
```

种子密码按优先级读取：环境变量 → Streamlit Secrets → 均未配置时随机兜底。想固定密码：本地复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml` 填入；云端在 App → ⋮ → Settings → Secrets 里添加同名 TOML。

#### 云端数据库（PostgreSQL / Supabase）

默认使用本地 SQLite（`data/guatfood.db`），适合本地单机。若部署到 Streamlit Cloud，SQLite 会因临时文件系统在重启/重新部署后丢失；此时应配置 `DATABASE_URL` 切换为托管 PostgreSQL：

1. 在 [Supabase](https://supabase.com) 免费建库，Dashboard → Settings → Database → Connection string 复制连接串。
   - **务必用「Session pooler」那条（端口 5432、IPv4）**，用户名形如 `postgres.<项目ref>`。
   - 「Direct connection」直连地址 `db.<ref>.supabase.co` 只解析 IPv6，部分网络连不上，别用。
2. 填入上面的 `DATABASE_URL`（本地 secrets 与 Streamlit Cloud Secrets 都填同一条）。
3. 首次部署后，运行 `py migrate_to_pg.py` 把本地 SQLite 数据一次性迁移到云端。

#### 图片对象存储（Supabase Storage）

图片默认存本地 `uploads/`，但 Streamlit Cloud 的文件系统是临时的，重启后图片会丢、线上也看不到。要让图片在线上持久显示（种子图 + 用户投稿 / 后台新上传图），需把图片放到 Supabase Storage 公开桶：

1. 在 Supabase Dashboard → Storage 建一个 **public** 桶 `food-images`。
2. 在 Dashboard → SQL Editor 执行两条「匿名」策略（SELECT 供上传流程读取元数据、INSERT 供上传）：
   ```sql
   create policy "food_images_anon_select" on storage.objects for select to anon using (bucket_id = 'food-images');
   create policy "food_images_anon_insert" on storage.objects for insert to anon with check (bucket_id = 'food-images');
   ```
3. 在 Secrets 里配置 `SUPABASE_ANON_KEY`（Dashboard → Settings → API → anon）。

> ⚠️ 安全提示：anon key 是公开的，这条策略意味着「知道 anon key 的人都能往你的桶传文件」，适合个人小站。如需更严，请改用 Supabase Auth + 按用户 RLS。

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
