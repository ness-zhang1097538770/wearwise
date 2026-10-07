"""穿搭生成：天气感知 + 规则筛选（温度硬约束 + 场景加分）+ LLM 润色。"""
from __future__ import annotations

import re

from app.core.logging import logger
from app.services import llm_client, parsers, weather_service
from app.services.prompts import render

# 场景 → 风格关键词（用于规则打分）
SCENE_STYLE_KEYWORDS = {
    "通勤": ["简约", "商务", "正式", "职场", "通勤", "干练", "利落", "基础"],
    "约会": ["优雅", "温柔", "浪漫", "甜美", "气质", "复古"],
    "运动": ["休闲", "运动", "街头", "户外", "宽松"],
    "面试": ["正式", "商务", "干练", "利落", "简约"],
    "聚会": ["时尚", "个性", "亮眼", "街头", "精致"],
    "旅行": ["休闲", "舒适", "户外", "运动", "百搭"],
    "日常": ["简约", "休闲", "日常", "百搭", "基础"],
}

_CORE_CATEGORIES = ("上装", "下装", "外套", "鞋", "配饰")


def _parse_temp(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", text or "")
    return float(m.group()) if m else None


async def _resolve_weather(requirements: dict) -> tuple[dict, dict]:
    location = (requirements.get("location") or "").strip()
    if location:
        try:
            weather = await weather_service.get_weather(location)
            return weather, weather_service.temperature_profile(weather["feels_like"])
        except Exception as e:  # noqa: BLE001
            logger.warning("天气获取失败，回退到手动输入: %s", e)
    feels = _parse_temp(requirements.get("weather") or "")
    tp = weather_service.temperature_profile(feels)
    weather = {
        "location": "",
        "temperature": feels,
        "feels_like": feels,
        "condition": (requirements.get("weather") or "").strip() or "未知",
        "humidity": None,
        "wind_speed": None,
    }
    return weather, tp


def _normalize_category(cat: str) -> str | None:
    if cat in ("上装", "下装", "外套", "鞋"):
        return cat
    if cat in ("包", "配饰", "帽子", "围巾"):
        return "配饰"
    if cat == "连衣裙":
        return "上装"
    return None


def _scene_keywords(scene: str) -> list[str]:
    for key, kws in SCENE_STYLE_KEYWORDS.items():
        if key in scene or scene in key:
            return kws
    return []


def _rank_garments(garments: list[dict], temp_profile: dict, scene: str) -> dict[str, list[dict]]:
    allowed = temp_profile["allowed_seasons"]
    keywords = _scene_keywords(scene)
    categories: dict[str, list[dict]] = {c: [] for c in _CORE_CATEGORIES}
    for g in garments:
        cat = _normalize_category(g.get("category", "其他"))
        if cat is None:
            continue
        if not weather_service.season_compatible(g.get("season", ""), allowed):
            continue  # 温度硬约束
        score = 5
        reasons = [f"季节匹配{temp_profile['label']}温度"]
        text = f"{g.get('style','')} {g.get('name','')}"
        if keywords and any(k in text for k in keywords):
            score += 2
            reasons.append(f"风格匹配「{scene}」场景")
        categories[cat].append({"garment": g, "score": score, "reasons": reasons})
    for cat in categories:
        categories[cat].sort(key=lambda x: -x["score"])
    return categories


def _build_outfits(categories: dict[str, list[dict]], temp_profile: dict) -> list[dict]:
    outfits: list[dict] = []
    for i in range(3):
        items: dict[str, str] = {}
        reasons: list[str] = []
        for cat in _CORE_CATEGORIES:
            ranked = categories[cat]
            if not ranked:
                continue
            # 上装用轮换产生差异，其余尽量取最优/次优
            if cat == "上装":
                idx = i % len(ranked)
            else:
                idx = min(i, len(ranked) - 1)
            entry = ranked[idx]
            items[cat] = entry["garment"]["name"]
            reasons.append(f"{cat}「{entry['garment']['name']}」：{'，'.join(entry['reasons'])}")
        if items:
            outfits.append({
                "name": f"方案 {i + 1}",
                "items": items,
                "reasons": reasons,
                "scores": {"场景": 0, "天气": 0, "风格": 0, "舒适度": 0},
            })
    return outfits


async def _llm_polish(outfits: list[dict], weather: dict, temp_profile: dict, scene: str, style: str) -> list[dict]:
    """LLM 只润色 name/reasons/scores，items 保持规则选出的结果不变。"""
    try:
        prompt = render(
            "outfit_polish",
            WEATHER=f"体感 {weather.get('feels_like')}°C，{weather.get('condition','')}",
            PROFILE=f"{temp_profile['label']}（{temp_profile['advice']}）",
            SCENE=scene or "日常",
            STYLE=style or "",
            OUTFITS=str(outfits),
        )
        raw = await llm_client.chat([{"role": "user", "content": prompt}])
        plan = parsers.parse_outfit_plan(raw)
        polished = plan["outfits"]
        # 用规则 items 覆盖 LLM 返回的 items（保证来自衣柜），保留 LLM 的 name/reasons/scores
        for i, o in enumerate(outfits):
            if i < len(polished):
                o["name"] = polished[i].get("name") or o["name"]
                o["reasons"] = polished[i].get("reasons") or o["reasons"]
                o["scores"] = polished[i].get("scores") or o["scores"]
        return outfits
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 润色失败，使用规则理由: %s", e)
        return outfits


async def generate_plan(garments: list[dict], requirements: dict) -> dict:
    """生成 3 套穿搭方案（规则筛选 + LLM 润色）。"""
    weather, temp_profile = await _resolve_weather(requirements)
    scene = requirements.get("scene") or "日常"
    categories = _rank_garments(garments, temp_profile, scene)
    if not any(categories.values()):
        # 温度硬约束下无可用衣物，放宽到全季节再试一次
        relaxed = {"label": "全季节", "allowed_seasons": {"春", "夏", "秋", "冬"}, "advice": ""}
        categories = _rank_garments(garments, relaxed, scene)
    outfits = _build_outfits(categories, temp_profile)
    if not outfits:
        raise ValueError("衣柜中没有可搭配的衣物")
    polished = await _llm_polish(outfits, weather, temp_profile, scene, requirements.get("style", ""))
    return {
        "outfits": polished,
        "weather": {
            "location": weather.get("location", ""),
            "feels_like": weather.get("feels_like"),
            "condition": weather.get("condition"),
            "temperature_rule": {"label": temp_profile["label"], "advice": temp_profile["advice"]},
        },
    }
