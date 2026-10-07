"""天气服务：Open-Meteo 免费接口（无需 Key），地理编码 + 实时天气 + 温度分档。"""
from __future__ import annotations

import time

import httpx

from app.core.logging import logger

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# 简单内存缓存（天气为临时外部数据，重启后重新拉取即可）
_cache: dict[str, tuple[float, dict]] = {}
_GEO_TTL = 7 * 24 * 3600
_WEATHER_TTL = 30 * 60

_WEATHER_CODE_TEXT = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "阵雨", 82: "强阵雨",
    95: "雷暴", 96: "雷暴伴冰雹", 99: "雷暴伴冰雹",
}


def _cached(key: str, ttl: float):
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < ttl:
            return val
    return None


def _set_cache(key: str, val: dict):
    _cache[key] = (time.time(), val)


async def _get(url: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def _geocode(location: str) -> tuple[float, float, str]:
    cached = _cached(f"geo:{location}", _GEO_TTL)
    if cached:
        return cached["lat"], cached["lon"], cached["name"]
    data = await _get(_GEO_URL, {"name": location, "count": 1, "language": "zh"})
    results = data.get("results") or []
    if not results:
        raise ValueError(f"未找到地点：{location}")
    r = results[0]
    val = {"lat": r["latitude"], "lon": r["longitude"], "name": r.get("name", location)}
    _set_cache(f"geo:{location}", val)
    return val["lat"], val["lon"], val["name"]


async def get_weather(location: str) -> dict:
    """返回 {location, temperature, feels_like, condition, humidity, wind_speed}。"""
    cached = _cached(f"weather:{location}", _WEATHER_TTL)
    if cached:
        return cached
    lat, lon, name = await _geocode(location)
    data = await _get(_WEATHER_URL, {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
    })
    cur = data["current"]
    code = cur.get("weather_code", 0)
    result = {
        "location": name,
        "temperature": cur.get("temperature_2m"),
        "feels_like": cur.get("apparent_temperature"),
        "condition": _WEATHER_CODE_TEXT.get(code, "未知"),
        "humidity": cur.get("relative_humidity_2m"),
        "wind_speed": cur.get("wind_speed_10m"),
    }
    _set_cache(f"weather:{location}", result)
    return result


# ---- 温度分档 ----

def temperature_profile(feels_like: float | None) -> dict:
    """按体感温度分 5 档，返回 {label, allowed_seasons, advice}。"""
    if feels_like is None:
        return {"label": "舒适", "allowed_seasons": {"春", "秋"}, "advice": "温度适中，保持透气与层次"}
    if feels_like <= 5:
        return {"label": "寒冷", "allowed_seasons": {"冬"}, "advice": "优先保暖，厚实上衣、长裤和保暖鞋"}
    if feels_like <= 14:
        return {"label": "偏凉", "allowed_seasons": {"秋", "冬"}, "advice": "轻量叠穿，外套和长裤优先"}
    if feels_like <= 24:
        return {"label": "舒适", "allowed_seasons": {"春", "秋"}, "advice": "温度适中，保持透气与层次"}
    if feels_like <= 30:
        return {"label": "偏热", "allowed_seasons": {"春", "夏"}, "advice": "优先透气轻薄单品"}
    return {"label": "炎热", "allowed_seasons": {"夏"}, "advice": "吸汗速干、透气面料，减少叠穿"}


def season_compatible(season: str, allowed_seasons: set[str]) -> bool:
    if season == "四季":
        return True
    if season in ("不确定", ""):
        return False
    return season in allowed_seasons
