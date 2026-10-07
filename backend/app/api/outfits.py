"""穿搭方案接口：SSE 流式生成、列表/详情、平铺图任务提交、收藏。"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.errors import AppError, error_body
from app.models.db import SessionLocal, get_db
from app.models.entities import Garment, Outfit, Task
from app.schemas.entities import OutfitCreate
from app.services import avatar_service, imaging, outfit_service, video_service

router = APIRouter(prefix="/outfits", tags=["outfits"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
def create_outfit(payload: OutfitCreate, db: Session = Depends(get_db)):
    garments = [g.to_dict() for g in db.query(Garment).filter(Garment.status == "confirmed").all()]
    if not garments:
        raise AppError("no_garments", "请先录入并确认至少 1 件衣物")

    outfit = Outfit(inputs_json=payload.model_dump(), status="pending")
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    outfit_id = outfit.id
    requirements = payload.model_dump()

    async def gen():
        try:
            yield _sse("chunk", {"text": "正在读取你的衣柜…"})
            plan = await outfit_service.generate_plan(garments, requirements)
            s = SessionLocal()
            try:
                o = s.get(Outfit, outfit_id)
                if o:
                    o.result_json = plan
                    o.status = "done"
                    s.commit()
            finally:
                s.close()
            yield _sse("chunk", {"text": "已生成 3 套方案"})
            yield _sse("done", {"outfit_id": outfit_id, "outfits": plan["outfits"], "weather": plan.get("weather", {})})
        except Exception as e:  # noqa: BLE001
            s = SessionLocal()
            try:
                o = s.get(Outfit, outfit_id)
                if o:
                    o.status = "failed"
                    s.commit()
            finally:
                s.close()
            yield _sse("error", error_body("generation_failed", "生成失败，请重试"))

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("")
def list_outfits(db: Session = Depends(get_db)):
    return [o.to_dict() for o in db.query(Outfit).order_by(Outfit.created_at.desc()).all()]


@router.get("/{outfit_id}")
def get_outfit(outfit_id: int, db: Session = Depends(get_db)):
    outfit = db.get(Outfit, outfit_id)
    if outfit is None:
        raise AppError("not_found", "方案不存在", 404)
    return outfit.to_dict()


@router.post("/{outfit_id}/items/{idx}/image", status_code=202)
def create_image(outfit_id: int, idx: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    outfit = db.get(Outfit, outfit_id)
    if outfit is None:
        raise AppError("not_found", "方案不存在", 404)
    task = Task(kind="image", outfit_id=outfit_id, item_index=idx, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(imaging.process_image_task, task.id)
    return {"task_id": task.id}


@router.post("/{outfit_id}/items/{idx}/avatar-image", status_code=202)
def create_avatar_image(outfit_id: int, idx: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    outfit = db.get(Outfit, outfit_id)
    if outfit is None:
        raise AppError("not_found", "方案不存在", 404)
    task = Task(kind="avatar_image", outfit_id=outfit_id, item_index=idx, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(avatar_service.process_avatar_outfit_task, task.id)
    return {"task_id": task.id}


@router.post("/{outfit_id}/items/{idx}/video", status_code=202)
def create_video(outfit_id: int, idx: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    outfit = db.get(Outfit, outfit_id)
    if outfit is None:
        raise AppError("not_found", "方案不存在", 404)
    task = Task(kind="video", outfit_id=outfit_id, item_index=idx, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(video_service.process_video_task, task.id)
    return {"task_id": task.id}


@router.post("/{outfit_id}/favorite")
def toggle_favorite(outfit_id: int, db: Session = Depends(get_db)):
    outfit = db.get(Outfit, outfit_id)
    if outfit is None:
        raise AppError("not_found", "方案不存在", 404)
    outfit.favorite = 0 if outfit.favorite else 1
    db.commit()
    db.refresh(outfit)
    return outfit.to_dict()
