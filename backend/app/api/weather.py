"""天气接口：按城市查询实时天气（Open-Meteo 免费）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import AppError
from app.services import weather_service

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("")
async def get_weather(location: str):
    if not location.strip():
        raise AppError("invalid_param", "请提供 location 参数（城市名）")
    try:
        return await weather_service.get_weather(location.strip())
    except Exception as e:  # noqa: BLE001
        raise AppError("weather_failed", f"天气获取失败：{e}")
