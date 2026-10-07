"""模型调用客户端：统一超时、失败、有限重试；无 Key 时走 mock。

- chat：文本对话（穿搭推荐）
- vision：视觉识别（衣物标签）
- generate_image：图像生成（平铺图）
mock 模式返回确定性结果，用于无 Key 开发与自动化测试；真实冒烟走火山方舟 OpenAI 兼容接口。
"""
from __future__ import annotations

import base64
import struct
import zlib
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def make_placeholder_png(path: Path, width: int = 600, height: int = 800, rgb: tuple = (216, 211, 205)) -> Path:
    """生成纯色占位 PNG（mock 成像用），无第三方依赖。"""
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    return path


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"}


async def _post_with_retry(url: str, payload: dict, retries: int = 2) -> dict:
    """带有限重试的 POST；SDK/网络失败统一抛 RuntimeError。"""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                resp = await client.post(url, headers=_headers(), json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:  # noqa: BLE001 - 统一兜底
            last_err = e
            logger.warning("模型调用失败（第 %s 次）: %s", attempt + 1, e)
    raise RuntimeError(f"模型调用失败: {last_err}")


async def chat(messages: list[dict], model: str | None = None) -> str:
    """文本对话，返回模型文本输出。"""
    model = model or settings.text_model
    if settings.use_mock:
        return _mock_chat(messages)
    data = await _post_with_retry(
        f"{settings.ark_base_url}/chat/completions",
        {"model": model, "messages": messages, "thinking": {"type": "disabled"}},
    )
    return data["choices"][0]["message"]["content"]


async def vision(image_path: str, prompt: str, model: str | None = None) -> str:
    """视觉识别：图片（base64）+ 文本提示。"""
    model = model or settings.vision_model
    if settings.use_mock:
        return _mock_vision()
    b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    ext = Path(image_path).suffix.lstrip(".").lower() or "jpeg"
    data = await _post_with_retry(
        f"{settings.ark_base_url}/chat/completions",
        {
            "model": model,
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
                    ],
                }
            ],
        },
    )
    return data["choices"][0]["message"]["content"]


def _sniff_image_format(content: bytes) -> str:
    if content[:4] == b"\x89PNG":
        return ".png"
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return ".png"


def _build_image_payload(prompt: str, num: int, reference_paths: list[str] | None) -> dict:
    payload: dict = {"model": settings.image_model, "prompt": prompt, "size": "1920x1920", "n": num}
    if reference_paths:
        refs = []
        for p in reference_paths:
            ext = Path(p).suffix.lstrip(".").lower() or "jpeg"
            b64 = base64.b64encode(Path(p).read_bytes()).decode()
            refs.append(f"data:image/{ext};base64,{b64}")
        payload["image"] = refs
    return payload


async def _download_item(item: dict) -> bytes:
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(item["url"])
            resp.raise_for_status()
            return resp.content
    raise RuntimeError("图像生成返回缺少数据")


async def generate_image(
    prompt: str,
    save_path: Path,
    model: str | None = None,
    reference_paths: list[str] | None = None,
) -> Path:
    """图像生成（单张）：返回保存后的图片路径（按真实格式定后缀）。
    reference_paths 传入参考图（图生图），如 Avatar 形象图。"""
    if settings.use_mock:
        return make_placeholder_png(save_path)
    data = await _post_with_retry(
        f"{settings.ark_base_url}/images/generations",
        _build_image_payload(prompt, 1, reference_paths),
    )
    content = await _download_item(data["data"][0])
    final_path = save_path.with_suffix(_sniff_image_format(content))
    final_path.write_bytes(content)
    return final_path


async def generate_images(
    prompt: str,
    save_dir: Path,
    prefix: str,
    num: int = 4,
    reference_paths: list[str] | None = None,
) -> list[Path]:
    """图像生成（多张）：并行生成 num 张，返回保存路径列表。
    （Seedream 对 n>1 支持不稳，改用并行单张请求）"""
    if settings.use_mock:
        return [make_placeholder_png(save_dir / f"{prefix}_{i}.png") for i in range(num)]
    import asyncio

    async def _one(i: int) -> Path:
        return await generate_image(prompt, save_dir / f"{prefix}_{i}.png", reference_paths=reference_paths)

    return await asyncio.gather(*[_one(i) for i in range(num)])


# ---- mock 实现（确定性，供开发与测试） ----

def _mock_vision() -> str:
    import json
    return json.dumps({
        "name": "白色衬衫",
        "category": "上装",
        "color": "白",
        "pattern": "纯色",
        "material": "棉",
        "fit": "合身",
        "season": "四季",
        "style": "简约",
    }, ensure_ascii=False)


def _mock_chat(messages: list[dict]) -> str:
    import json
    # 提取用户最后一条文本，忽略系统 prompt
    last = ""
    for m in reversed(messages):
        c = m.get("content")
        if isinstance(c, str):
            last = c
            break
    return json.dumps({
        "outfits": [
            {
                "name": "通勤清爽款",
                "items": {"上装": "白色衬衫", "下装": "藏青直筒裤", "鞋": "乐福鞋", "配饰": "简约手表"},
                "reasons": ["白色衬衫百搭且适合办公场合", "藏青直筒裤显利落，与白衬衫配色协调"],
                "scores": {"场景": 9, "天气": 8, "风格": 8, "舒适度": 9},
            },
            {
                "name": "休闲舒适款",
                "items": {"上装": "针织衫", "下装": "牛仔裤", "鞋": "运动鞋", "配饰": "帆布包"},
                "reasons": ["针织衫舒适保暖", "牛仔裤与运动鞋适合日常走动"],
                "scores": {"场景": 8, "天气": 8, "风格": 7, "舒适度": 9},
            },
            {
                "name": "优雅正式款",
                "items": {"上装": "西装外套", "下装": "西装裤", "鞋": "高跟鞋", "配饰": "手提包"},
                "reasons": ["西装外套提升正式感", "同色系搭配显高级"],
                "scores": {"场景": 9, "天气": 7, "风格": 9, "舒适度": 7},
            },
        ]
    }, ensure_ascii=False)
