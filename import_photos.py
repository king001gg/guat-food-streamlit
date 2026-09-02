"""一次性导入：把一批美食照片压缩后作为「菜品」写入数据库。

用法：
    py import_photos.py "E:/Users/MECHREVO/Downloads/113APPLE_IMG_3606等51项文件"
    py import_photos.py "<照片目录>" --canteen 校外 --window 美食图鉴

行为：
- 每张照片 = 一道菜，命名「菜品01…菜品NN」（占位，之后在后台改名）。
- 照片压缩到 800×800、JPEG 质量 85，存到 uploads/seed/NN.jpg。
- 自动跳过文件名含 " (1)." 的重复副本（去重）。
- 后端与 app 一致：secrets.toml 里配了 DATABASE_URL 就写 PostgreSQL，否则写本地 SQLite。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SEED_DIR_NAME = "seed"


def _apply_db_url() -> None:
    """与 app.py 保持一致：secrets.toml 有 DATABASE_URL 就切换到 PG，否则 SQLite。"""
    if os.environ.get("DATABASE_URL"):
        return
    secrets_path = ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import tomllib

            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
            if data.get("DATABASE_URL"):
                os.environ["DATABASE_URL"] = str(data["DATABASE_URL"])
        except Exception:
            pass


def _unique_photos(folder: Path) -> list[Path]:
    """按文件名排序返回唯一照片，跳过 " (1)." 之类的重复副本。"""
    return [
        p
        for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and " (1)." not in p.name
    ]


def _compress(src: Path, dst: Path) -> None:
    from PIL import Image

    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((800, 800))
        im.save(dst, "JPEG", quality=85)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("用法：py import_photos.py <照片目录> [--canteen 校外] [--window 美食图鉴]")
        sys.exit(1)

    folder = Path(args[0]).expanduser()
    if not folder.is_dir():
        print(f"目录不存在：{folder}")
        sys.exit(1)

    canteen_name = "校外"
    window_name = "美食图鉴"
    it = iter(args[1:])
    for a in it:
        if a == "--canteen":
            canteen_name = next(it)
        elif a == "--window":
            window_name = next(it)

    photos = _unique_photos(folder)
    if not photos:
        print("未找到可导入的照片（支持 .jpg/.jpeg/.png/.webp/.bmp）")
        sys.exit(1)

    _apply_db_url()
    from core import db  # 双后端：读环境变量 DATABASE_URL

    db.ensure_dirs()
    seed_dir = db.UPLOAD_DIR / SEED_DIR_NAME
    seed_dir.mkdir(exist_ok=True)

    # 食堂：幂等（name 唯一）
    db.execute(
        "INSERT INTO canteen (name, location, sort_order) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
        (canteen_name, "商业街", 99),
    )
    canteen = db.query_one("SELECT id FROM canteen WHERE name = ?", (canteen_name,))
    if not canteen:
        print("无法创建/找到食堂，中止")
        sys.exit(1)

    # 档口：同名复用，不存在则新建
    win = db.query_one(
        "SELECT id FROM food_window WHERE name = ? AND canteen_id = ?",
        (window_name, canteen["id"]),
    )
    if win:
        wid = win["id"]
    else:
        wid = db.execute(
            "INSERT INTO food_window (canteen_id, name, description, location, status) "
            "VALUES (?, ?, ?, ?, 'PUBLISHED')",
            (canteen["id"], window_name, "个人美食图鉴（占位菜名，可在后台修改）", "图鉴"),
        )

    n = 0
    skipped = 0
    for i, src in enumerate(photos, 1):
        name = f"菜品{i:02d}"
        dst = seed_dir / f"{i:02d}.jpg"
        _compress(src, dst)
        rel = f"uploads/{SEED_DIR_NAME}/{dst.name}"

        # 幂等：同档口下已有同名菜品则跳过
        if db.query_one("SELECT id FROM dish WHERE window_id = ? AND name = ?", (wid, name)):
            skipped += 1
            continue
        db.execute(
            "INSERT INTO dish (window_id, name, description, image, price, status) "
            "VALUES (?, ?, ?, ?, ?, 'PUBLISHED')",
            (wid, name, "", rel, 0.0),
        )
        n += 1

    print(f"导入完成：新增 {n} 道菜" + (f"，跳过已存在 {skipped} 道" if skipped else "") + f"")
    print(f"  档口「{window_name}」→ 食堂「{canteen_name}」")
    print(f"  照片已压缩到 uploads/{SEED_DIR_NAME}/（{len(photos)} 张）")


if __name__ == "__main__":
    main()
