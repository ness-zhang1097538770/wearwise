"""购物防冲动分析服务：视觉提取商品信息 + 文字分析报告。"""
from __future__ import annotations

from app.core.logging import logger
from app.services import llm_client, parsers
from app.services.prompts import load, render


def _wardrobe_text(garments: list[dict]) -> str:
    lines = []
    for g in garments:
        parts = [g.get("name") or "未命名"]
        for key in ("category", "color", "pattern", "material", "fit", "season"):
            v = g.get(key)
            if v and v != "不确定":
                parts.append(str(v))
        lines.append("- " + "/".join(parts))
    return "\n".join(lines) if lines else "（衣柜为空）"


def parse_analysis_report(text: str) -> dict:
    """解析分析报告 JSON，缺失字段给默认值（不阻断）。"""
    try:
        obj = parsers.extract_json(text)
    except Exception:
        obj = {}
    if not isinstance(obj, dict):
        obj = {}
    return {
        "match_score": obj.get("match_score", 0),
        "match_reason": obj.get("match_reason", ""),
        "duplicate_score": obj.get("duplicate_score", 0),
        "duplicate_reason": obj.get("duplicate_reason", ""),
        "similar_items": obj.get("similar_items", []) or [],
        "can_pair_count": obj.get("can_pair_count", 0),
        "pair_examples": obj.get("pair_examples", []) or [],
        "cost_per_wear": obj.get("cost_per_wear", ""),
        "suggestion": obj.get("suggestion", "建议等待"),
        "suggestion_reason": obj.get("suggestion_reason", ""),
    }


async def analyze(image_path: str, garments: list[dict]) -> dict:
    """返回 {product, report}。"""
    # 1. 视觉提取商品信息
    try:
        raw_product = await llm_client.vision(image_path, load("analysis_product"))
        product = parsers.parse_garment_tags(raw_product)
    except Exception as e:  # noqa: BLE001
        logger.warning("商品信息提取失败: %s", e)
        product = {"name": "", "category": "其他", "color": "不确定", "pattern": "不确定",
                   "material": "不确定", "fit": "不确定", "season": "不确定", "style": ""}

    # 2. 文字分析报告
    prompt = render("analysis", PRODUCT=str(product), WARDROBE=_wardrobe_text(garments))
    try:
        raw_report = await llm_client.chat([{"role": "user", "content": prompt}])
        report = parse_analysis_report(raw_report)
    except Exception as e:  # noqa: BLE001
        logger.warning("分析报告生成失败: %s", e)
        report = parse_analysis_report("")

    return {"product": product, "report": report}
