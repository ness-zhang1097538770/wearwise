"""上传校验测试：真实类型嗅探、大小、格式、安全文件名。"""
import asyncio
from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.errors import AppError
from app.services.files import _sniff_type, save_upload


def test_sniff_types():
    assert _sniff_type(b"\xff\xd8\xff\xe0" + b"x" * 8) == ".jpg"
    assert _sniff_type(b"\x89PNG\r\n\x1a\n" + b"x" * 8) == ".png"
    assert _sniff_type(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"x" * 8) == ".webp"
    assert _sniff_type(b"notanimage") is None


def _upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


def test_save_upload_ok():
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 32
    path = asyncio.run(save_upload(_upload("a.png", png)))
    assert path.name.endswith(".png")


def test_save_upload_rejects_bad_ext():
    with pytest.raises(AppError) as e:
        asyncio.run(save_upload(_upload("a.txt", b"\x89PNG\r\n\x1a\n")))
    assert e.value.code == "invalid_file_type"


def test_save_upload_rejects_fake_content():
    # .png 后缀但内容不是图片
    with pytest.raises(AppError) as e:
        asyncio.run(save_upload(_upload("a.png", b"not really a png")))
    assert e.value.code == "invalid_file_content"


def test_save_upload_rejects_oversize(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.get_settings(), "max_upload_mb", 0)  # 任何内容都超限
    # 重置缓存后重新取
    config.get_settings.cache_clear()
    try:
        png = b"\x89PNG\r\n\x1a\n" + b"x" * 100
        with pytest.raises(AppError) as e:
            asyncio.run(save_upload(_upload("a.png", png)))
        assert e.value.code == "file_too_large"
    finally:
        config.get_settings.cache_clear()
