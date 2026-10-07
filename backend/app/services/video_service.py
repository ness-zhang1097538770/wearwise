"""动态试穿视频服务：Seedance 图生视频（异步：提交 → 轮询 → 下载）。"""
from __future__ import annotations

import base64
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.models.db import SessionLocal
from app.models.entities import Outfit, Task
from app.services import llm_client
from app.services.prompts import render

settings = get_settings()

_VIDEO_API = f"{settings.ark_base_url}/contents/generations/tasks"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"}


async def _submit_video(image_path: str, prompt: str) -> str:
    ext = Path(image_path).suffix.lstrip(".").lower() or "jpeg"
    b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(
            _VIDEO_API,
            headers=_headers(),
            json={
                "model": settings.video_model,
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def _poll_video(task_id: str) -> dict:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.get(f"{_VIDEO_API}/{task_id}", headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def _download_video(url: str, save_path: Path) -> Path:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        save_path.write_bytes(resp.content)
    return save_path


def _latest_avatar_image_path(db, outfit_id: int, item_index: int) -> str | None:
    """找该套穿搭最近一次生成的上身图本地路径。"""
    task = (
        db.query(Task)
        .filter(
            Task.kind == "avatar_image",
            Task.outfit_id == outfit_id,
            Task.item_index == item_index,
            Task.status == "done",
        )
        .order_by(Task.created_at.desc())
        .first()
    )
    if task is None or not task.result_json.get("image_url"):
        return None
    url = task.result_json["image_url"]
    return str(settings.generated_dir / url.split("/")[-1])


async def process_video_task(task_id: int) -> None:
    """用上身图作首帧，生成动态试穿视频。"""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        src = task.result_json.get("source_image") or _latest_avatar_image_path(
            db, task.outfit_id, task.item_index
        )
        if not src:
            task.status = "failed"
            task.error = "请先生成该套的上身图"
            db.commit()
            return

        if settings.use_mock:
            task.status = "done"
            task.result_json = {"video_url": None, "mock": True}
            db.commit()
            return

        prompt = render("video")
        ark_task_id = await _submit_video(src, prompt)
        for _ in range(60):  # 最多轮询约 10 分钟
            data = await _poll_video(ark_task_id)
            status = data.get("status")
            if status == "succeeded":
                video_url = (data.get("content") or {}).get("video_url")
                if not video_url:
                    raise RuntimeError("视频任务成功但缺少 video_url")
                save_path = settings.generated_dir / f"video_{task_id}.mp4"
                await _download_video(video_url, save_path)
                task.status = "done"
                task.result_json = {
                    "video_url": f"/static/generated/{save_path.name}",
                    "duration": data.get("duration"),
                    "resolution": data.get("resolution"),
                }
                db.commit()
                return
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"视频任务状态: {status}")
            import asyncio
            await asyncio.sleep(10)
        raise RuntimeError("视频生成超时")

    except Exception as e:  # noqa: BLE001
        logger.warning("视频生成失败: %s", e)
        try:
            task = db.get(Task, task_id)
            if task:
                task.status = "failed"
                task.error = "视频生成失败，请重试（不扣额度）"
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()
