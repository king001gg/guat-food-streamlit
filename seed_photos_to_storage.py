"""一次性：把 uploads/seed/ 的压缩照片上传到 Supabase Storage 公开桶，并把 dish.image 更新为公开 URL。

用法：
    py seed_photos_to_storage.py "<anon key>"

说明：
- 用数据库超级权限建公开桶 + 建三条「anon 可读写该桶」的临时策略（SELECT/INSERT/UPDATE），
  传完立刻删掉全部策略，桶保持「只读公开」状态（任何人能看图，但不能再上传/改写）。
- 只更新 image = 'uploads/seed/NN.jpg' 的菜品，不碰其它菜品/档口。
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

REF = "jyimjkegqjgwrwweflxv"
BUCKET = "food-images"
SEED_DIR = "seed"
BASE = f"https://{REF}.supabase.co"
PUBLIC_PREFIX = f"{BASE}/storage/v1/object/public"

# (策略名, 建策略 SQL)；上传期间临时生效，传完删除
POLICIES = [
    (
        "seed_upload_sel",
        f"CREATE POLICY \"seed_upload_sel\" ON storage.objects FOR SELECT TO anon "
        f"USING (bucket_id = '{BUCKET}')",
    ),
    (
        "seed_upload_ins",
        f"CREATE POLICY \"seed_upload_ins\" ON storage.objects FOR INSERT TO anon "
        f"WITH CHECK (bucket_id = '{BUCKET}')",
    ),
    (
        "seed_upload_upd",
        f"CREATE POLICY \"seed_upload_upd\" ON storage.objects FOR UPDATE TO anon "
        f"USING (bucket_id = '{BUCKET}') WITH CHECK (bucket_id = '{BUCKET}')",
    ),
]
# 之前调试残留的策略名，一并清掉
LEFTOVERS = ["food_images_anon_upload_tmp", "food_images_anon_tmp_sel", "food_images_anon_tmp_ins"]


def _apply_db_url() -> None:
    """与 app.py 一致：secrets.toml 有 DATABASE_URL 就切 PG。"""
    if os.environ.get("DATABASE_URL"):
        return
    p = ROOT / ".streamlit" / "secrets.toml"
    if p.exists():
        import tomllib

        with open(p, "rb") as f:
            data = tomllib.load(f)
        if data.get("DATABASE_URL"):
            os.environ["DATABASE_URL"] = str(data["DATABASE_URL"])


def _upload(anon: str, path: str, body: bytes) -> int:
    """上传单个文件，返回 HTTP 状态码。"""
    url = f"{BASE}/storage/v1/object/{path}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {anon}")
    req.add_header("Content-Type", "image/jpeg")
    req.add_header("x-upsert", "true")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> None:
    anon = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SUPABASE_ANON_KEY")
    if not anon:
        print("用法：py seed_photos_to_storage.py <anon key>")
        sys.exit(1)

    _apply_db_url()
    from core import db

    seed_dir = ROOT / "uploads" / SEED_DIR
    photos = sorted(seed_dir.glob("*.jpg"))
    if not photos:
        print(f"未找到照片：{seed_dir}")
        sys.exit(1)

    all_policy_names = [n for n, _ in POLICIES] + LEFTOVERS
    for n in all_policy_names:
        db.execute(f'DROP POLICY IF EXISTS "{n}" ON storage.objects')

    # 1) 建公开桶（幂等）
    db.execute(
        "INSERT INTO storage.buckets (id, name, public) VALUES (?, ?, true) "
        "ON CONFLICT (id) DO NOTHING",
        (BUCKET, BUCKET),
    )
    # 2) 建临时上传策略
    for _, stmt in POLICIES:
        db.execute(stmt)

    try:
        # 3) 上传
        uploaded = []
        for f in photos:
            path = f"{BUCKET}/{SEED_DIR}/{f.name}"
            code = _upload(anon, path, f.read_bytes())
            if code not in (200, 201):
                print(f"上传失败 {f.name}: HTTP {code}")
                sys.exit(1)
            uploaded.append((f.name, f"{PUBLIC_PREFIX}/{path}"))

        # 4) 更新 dish.image
        for name, url in uploaded:
            db.execute(
                "UPDATE dish SET image = ? WHERE image = ?",
                (url, f"uploads/{SEED_DIR}/{name}"),
            )
    finally:
        # 5) 删掉临时策略（只读公开，不能再上传/改写）
        for n in all_policy_names:
            db.execute(f'DROP POLICY IF EXISTS "{n}" ON storage.objects')

    total = db.query_one(
        "SELECT COUNT(*) AS c FROM dish WHERE image LIKE ?",
        (f"{PUBLIC_PREFIX}/{BUCKET}/{SEED_DIR}/%",),
    )
    print(f"上传成功 {len(uploaded)} 张，dish.image 已更新为公开 URL 共 {total['c']} 行")
    print("临时策略已全部删除，桶保持只读公开。")


if __name__ == "__main__":
    main()
