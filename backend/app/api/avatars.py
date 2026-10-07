"""Avatar 数字形象接口：生成候选、列表、选择主形象、删除。"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.db import get_db
from app.models.entities import Avatar, Task
from app.schemas.entities import AvatarCreate
from app.services import avatar_service

router = APIRouter(prefix="/avatars", tags=["avatars"])


@router.post("", status_code=201)
def create_avatar(payload: AvatarCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    avatar = Avatar(params_json=payload.model_dump(), status="pending")
    db.add(avatar)
    db.commit()
    db.refresh(avatar)
    background_tasks.add_task(avatar_service.process_avatar_task, avatar.id)
    return avatar.to_dict()


@router.get("")
def list_avatars(db: Session = Depends(get_db)):
    return [a.to_dict() for a in db.query(Avatar).order_by(Avatar.created_at.desc()).all()]


@router.get("/{avatar_id}")
def get_avatar(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.get(Avatar, avatar_id)
    if avatar is None:
        raise AppError("not_found", "形象不存在", 404)
    return avatar.to_dict()


@router.post("/{avatar_id}/select")
def select_avatar(avatar_id: int, payload: dict, db: Session = Depends(get_db)):
    avatar = db.get(Avatar, avatar_id)
    if avatar is None:
        raise AppError("not_found", "形象不存在", 404)
    index = payload.get("index")
    if index is None or not isinstance(index, int) or index < 0 or index >= len(avatar.candidates_json or []):
        raise AppError("invalid_index", "候选序号不合法")
    # 先取消旧主形象
    for a in db.query(Avatar).filter(Avatar.is_primary == 1).all():
        a.is_primary = 0
    avatar.selected = index
    avatar.is_primary = 1
    db.commit()
    db.refresh(avatar)
    return avatar.to_dict()


@router.post("/{avatar_id}/fuse", status_code=202)
def fuse_avatar(avatar_id: int, payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    avatar = db.get(Avatar, avatar_id)
    if avatar is None:
        raise AppError("not_found", "形象不存在", 404)
    face_index = payload.get("face_index")
    body_index = payload.get("body_index")
    if not isinstance(face_index, int) or not isinstance(body_index, int):
        raise AppError("invalid_index", "face_index/body_index 必须为整数")
    task = Task(kind="avatar_fuse", result_json={"avatar_id": avatar_id, "face_index": face_index, "body_index": body_index}, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(avatar_service.process_avatar_fuse_task, task.id)
    return {"task_id": task.id}


@router.delete("/{avatar_id}", status_code=204)
def delete_avatar(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.get(Avatar, avatar_id)
    if avatar is None:
        raise AppError("not_found", "形象不存在", 404)
    db.delete(avatar)
    db.commit()
    return None
