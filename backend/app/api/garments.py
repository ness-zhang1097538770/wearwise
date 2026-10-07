"""衣物接口：上传+识别（支持批量多张）+ 本地抠图、列表、修正、删除。"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import logger
from app.models.db import get_db
from app.models.entities import Garment
from app.schemas.entities import GarmentUpdate
from app.services import files as file_service, recognition
from app.services import segment

router = APIRouter(prefix="/garments", tags=["garments"])


@router.post("", status_code=201)
async def create_garments(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    """批量上传衣物照片，并行识别每件（含本地抠图白底），返回入库列表。"""
    settings = get_settings()

    async def _process(file: UploadFile):
        path = await file_service.save_upload(file)
        cutout_url = ""
        if settings.enable_cutout:
            try:
                cutout_bytes = await asyncio.to_thread(segment.remove_background_to_white, path.read_bytes())
                cutout_path = path.with_name(path.stem + "_cutout.jpg")
                cutout_path.write_bytes(cutout_bytes)
                cutout_url = cutout_path.name
            except Exception as e:  # noqa: BLE001
                logger.warning("抠图失败，保留原图: %s", e)
        tags = await recognition.recognize(str(path))
        return path, tags, cutout_url

    processed = await asyncio.gather(*[_process(f) for f in files])
    garments = []
    for path, tags, cutout_url in processed:
        g = Garment(image_path=str(path), tags_json={"cutout": cutout_url} if cutout_url else {}, **tags)
        db.add(g)
        garments.append(g)
    db.commit()
    for g in garments:
        db.refresh(g)
    return [g.to_dict() for g in garments]


@router.get("")
def list_garments(status: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Garment)
    if status:
        q = q.filter(Garment.status == status)
    if category:
        q = q.filter(Garment.category == category)
    return [g.to_dict() for g in q.order_by(Garment.created_at.desc()).all()]


@router.patch("/{garment_id}")
def update_garment(garment_id: int, payload: GarmentUpdate, db: Session = Depends(get_db)):
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise AppError("not_found", "衣物不存在", 404)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(garment, field, value)
    garment.status = "confirmed"
    db.commit()
    db.refresh(garment)
    return garment.to_dict()


@router.post("/{garment_id}/recognize")
async def re_recognize(garment_id: int, db: Session = Depends(get_db)):
    """对已有衣物重新跑真实视觉识别（用于修正旧 mock 数据的标签）。"""
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise AppError("not_found", "衣物不存在", 404)
    if not garment.image_path:
        raise AppError("no_image", "该衣物没有原图，请重新上传")
    tags = await recognition.recognize(garment.image_path)
    for field, value in tags.items():
        setattr(garment, field, value)
    garment.status = "draft"  # 重新识别后回到待确认，用户确认后变 confirmed
    db.commit()
    db.refresh(garment)
    return garment.to_dict()


@router.delete("/{garment_id}", status_code=204)
def delete_garment(garment_id: int, db: Session = Depends(get_db)):
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise AppError("not_found", "衣物不存在", 404)
    db.delete(garment)
    db.commit()
    return None
