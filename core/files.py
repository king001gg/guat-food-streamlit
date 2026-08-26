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


def resolve_image(relpath: str | None) -> Path | None:
    """把入库的相对路径解析为绝对路径，供 st.image 使用。"""
    if not relpath:
        return None
    path = Path(relpath)
    if not path.is_absolute():
        path = db.ROOT / path
    return path if path.exists() else None


def image_data_uri(relpath: str | None) -> str | None:
    """把入库的相对路径转为 base64 data URI，供自定义 HTML <img> 使用。"""
    path = resolve_image(relpath)
    if not path:
        return None
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None
