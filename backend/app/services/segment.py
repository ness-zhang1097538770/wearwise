"""rembg 本地抠图：背景移除 + 白底合成。"""
from __future__ import annotations

import io

from PIL import Image


def remove_background_to_white(image_bytes: bytes) -> bytes:
    """去除背景并合成白底，返回 JPEG 字节。"""
    from rembg import remove as rembg_remove  # 延迟导入，避免依赖缺失时报错

    input_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    output = rembg_remove(input_img)  # RGBA 透明背景
    # 合成白底
    white = Image.new("RGBA", output.size, (255, 255, 255, 255))
    white.paste(output, (0, 0), output)
    buf = io.BytesIO()
    white.convert("RGB").save(buf, format="JPEG", quality=95)
    return buf.getvalue()
