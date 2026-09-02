"""图片上传与本地存储。"""
from __future__ import annotations

import base64
import uuid
from pathlib import Path

from PIL import Image

from core import db


def save_image(uploaded) -> str | None:
    """压缩并保存上传图片，返回相对路径（uploads/xxx.jpg）或 None。"""
    if uploaded is None:
        return None
    try:
        image = Image.open(uploaded).convert("RGB")
        image.thumbnail((800, 800))
        name = f"{uuid.uuid4().hex}.jpg"
        path = db.UPLOAD_DIR / name
        image.save(path, "JPEG", quality=85)
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
