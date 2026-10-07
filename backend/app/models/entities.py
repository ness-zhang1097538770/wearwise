"""业务实体：衣物、穿搭方案、成像任务。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Garment(Base):
    __tablename__ = "garments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(30), default="其他")
    color: Mapped[str] = mapped_column(String(30), default="不确定")
    pattern: Mapped[str] = mapped_column(String(30), default="不确定")
    material: Mapped[str] = mapped_column(String(30), default="不确定")
    fit: Mapped[str] = mapped_column(String(30), default="不确定")
    season: Mapped[str] = mapped_column(String(30), default="不确定")
    style: Mapped[str] = mapped_column(String(100), default="")
    image_path: Mapped[str] = mapped_column(String(500), default="")
    tags_json: Mapped[dict] = mapped_column(JSON, default=dict)  # 预留：视觉指纹等
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft / confirmed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def to_dict(self) -> dict:
        cutout = (self.tags_json or {}).get("cutout", "")
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "color": self.color,
            "pattern": self.pattern,
            "material": self.material,
            "fit": self.fit,
            "season": self.season,
            "style": self.style,
            "image_url": f"/static/uploads/{self.image_path.split('/')[-1]}" if self.image_path else None,
            "cutout_url": f"/static/uploads/{cutout}" if cutout else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inputs_json: Mapped[dict] = mapped_column(JSON, default=dict)  # 天气/场合/风格等
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)  # 3 套方案
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/done/failed
    favorite: Mapped[bool] = mapped_column(Integer, default=0)  # 0/1
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "inputs": self.inputs_json,
            "result": self.result_json,
            "status": self.status,
            "favorite": bool(self.favorite),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), default="image")  # image / avatar_image
    outfit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/done/failed
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "outfit_id": self.outfit_id,
            "item_index": self.item_index,
            "status": self.status,
            "result": self.result_json,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Avatar(Base):
    __tablename__ = "avatars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)  # 体型参数
    candidates_json: Mapped[list] = mapped_column(JSON, default=list)  # [{index, image_url}]
    selected: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 选中的候选 index
    is_primary: Mapped[int] = mapped_column(Integer, default=0)  # 0/1 主形象
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/done/failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "params": self.params_json,
            "candidates": self.candidates_json,
            "selected": self.selected,
            "is_primary": bool(self.is_primary),
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_json: Mapped[dict] = mapped_column(JSON, default=dict)  # 商品信息
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)  # 分析报告
    image_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product": self.product_json,
            "report": self.report_json,
            "image_url": f"/static/uploads/{self.image_path.split('/')[-1]}" if self.image_path else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
