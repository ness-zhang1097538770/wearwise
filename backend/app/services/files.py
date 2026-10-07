"""文件上传校验与存储：格式、真实类型、大小、安全文件名。"""
from __future__ import annotations

import secrets
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()

_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# 真实类型魔数
_MAGIC = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG": ".png",
}


def _sniff_type(head: bytes) -> str | None:
    for magic, ext in _MAGIC.items():
        if head.startswith(magic):
            return ext
    # WEBP: RIFF....WEBP
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


async def save_upload(file: UploadFile) -> Path:
    """校验并保存上传图片，返回存储路径。"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise AppError("invalid_file_type", "仅支持 jpg / png / webp 图片")

    content = await file.read()
    if not content:
        raise AppError("empty_file", "文件为空")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise AppError("file_too_large", f"文件超过 {settings.max_upload_mb}MB 上限")

    # 真实类型嗅探（防止伪装扩展名）
    sniffed = _sniff_type(content[:16])
    if sniffed is None or (sniffed != ext and not (ext == ".jpg" and sniffed == ".jpeg")):
        raise AppError("invalid_file_content", "文件内容与图片格式不符")

    # 安全文件名（随机，防路径遍历）
    safe_name = f"{uuid.uuid4().hex}{ext if ext != '.jpeg' else '.jpg'}"
    path = settings.uploads_dir / safe_name
    path.write_bytes(content)
    return path
