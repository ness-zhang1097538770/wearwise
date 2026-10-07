"""Pydantic 输入输出结构。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class GarmentUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    color: str | None = None
    pattern: str | None = None
    material: str | None = None
    fit: str | None = None
    season: str | None = None
    style: str | None = None


class OutfitCreate(BaseModel):
    scene: str = Field(default="日常通勤", description="场合")
    weather: str = Field(default="", description="天气（手动输入，与 location 二选一）")
    location: str = Field(default="", description="城市（自动查天气，优先于 weather）")
    style: str = Field(default="", description="风格偏好")
    formal: str = Field(default="", description="正式程度")
    notes: str = Field(default="", description="补充要求")


class AvatarCreate(BaseModel):
    height: str = Field(default="", description="身高，如 165cm")
    build: str = Field(default="", description="体型，如 中等偏瘦")
    skin: str = Field(default="", description="肤色，如 自然肤色")
    hair: str = Field(default="", description="发色发型，如 黑色长发")
    age: str = Field(default="", description="年龄区间，如 25-30 岁")
    style: str = Field(default="写实", description="形象风格，MVP 仅写实")
