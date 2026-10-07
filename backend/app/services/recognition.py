"""衣物识别服务：视觉模型 + 宽容解析。"""
from __future__ import annotations

from app.core.logging import logger
from app.services import llm_client, parsers
from app.services.prompts import load


async def recognize(image_path: str) -> dict:
    prompt = load("recognition")
    try:
        raw = await llm_client.vision(image_path, prompt)
        tags = parsers.parse_garment_tags(raw)
    except Exception as e:  # noqa: BLE001
        # 识别失败不阻断：返回"不确定"标签，交用户人工填写
        logger.warning("衣物识别失败，返回待确认标签: %s", e)
        tags = {
            "name": "", "category": "其他", "color": "不确定", "pattern": "不确定",
            "material": "不确定", "fit": "不确定", "season": "不确定", "style": "",
        }
    return tags
