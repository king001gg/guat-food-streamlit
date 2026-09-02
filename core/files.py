"""图片上传与存储：优先 Supabase Storage（公开桶），未配置 anon key 时回退本地磁盘。"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

from core import db

STORAGE_BUCKET = "food-images"
USER_DIR = "user"  # 用户上传放在桶内 user/ 子目录，与种子图 seed/ 分开


def _ref_from_anon(anon: str) -> str | None:
    """从 anon key 的 JWT payload 里解析出项目 ref（无需额外配置 SUPABASE_URL）。"""
    try:
        payload = anon.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("ref")
    except Exception:
        return None


def _storage_config() -> tuple[str | None, str | None]:
    """返回 (supabase 根地址, anon key)；未配置 anon key 时返回 (None, None)。"""
    anon = os.environ.get("SUPABASE_ANON_KEY")
    if not anon:
        return None, None
    ref = _ref_from_anon(anon)
    if not ref:
        return None, None
    return f"https://{ref}.supabase.co", anon


def _upload_to_storage(name: str, data: bytes) -> str | None:
    """把图片字节上传到公开桶，返回公开 URL；失败或未配置时返回 None。"""
    base, anon = _storage_config()
    if not base:
        return None
    path = f"{USER_DIR}/{name}"
    url = f"{base}/storage/v1/object/{STORAGE_BUCKET}/{path}"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {anon}")
    req.add_header("Content-Type", "image/jpeg")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status in (200, 201):
                return f"{base}/storage/v1/object/public/{STORAGE_BUCKET}/{path}"
    except Exception:
        return None
    return None


def save_image(uploaded) -> str | None:
    """压缩上传图片；配置了 anon key 则传对象存储返回公开 URL，否则存本地返回相对路径。"""
    if uploaded is None:
        return None
    try:
        image = Image.open(uploaded).convert("RGB")
        image.thumbnail((800, 800))
        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=85)
        data = buf.getvalue()
        name = f"{uuid.uuid4().hex}.jpg"

        remote = _upload_to_storage(name, data)
        if remote:
            return remote

        db.ensure_dirs()
        path = db.UPLOAD_DIR / name
        path.write_bytes(data)
        return f"uploads/{name}"
    except Exception:
        return None


def _is_remote(value: str | None) -> bool:
    """是否为远程图片地址（公开 URL），无需再解析本地文件。"""
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def resolve_image(relpath: str | None) -> Path | str | None:
    """把入库的图片值解析为可显示对象：远程 URL 原样返回，本地路径解析为绝对路径。"""
    if not relpath:
        return None
    if _is_remote(relpath):
        return relpath
    path = Path(relpath)
    if not path.is_absolute():
        path = db.ROOT / path
    return path if path.exists() else None


def image_data_uri(relpath: str | None) -> str | None:
    """把入库的图片值转为 HTML <img src> 可用值：远程 URL 原样返回，本地路径转 base64 data URI。"""
    if not relpath:
        return None
    if _is_remote(relpath):
        return relpath
    path = resolve_image(relpath)
    if not path:
        return None
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None
