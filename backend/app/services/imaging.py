"""平铺图成像服务：提交 + 后台处理 + 轮询查询。"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import logger
from app.models.db import SessionLocal
from app.models.entities import Outfit, Task
from app.services import llm_client
from app.services.prompts import render

settings = get_settings()


def build_items_text(items: dict) -> str:
    parts = []
    for slot, name in items.items():
        if name:
            parts.append(f"{slot}：{name}")
    return "；".join(parts) if parts else "基础百搭单品"


async def process_image_task(task_id: int) -> None:
    """后台执行平铺图生成，状态持久化，失败可恢复。"""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        items_text = ""
        if task.outfit_id is not None:
            outfit = db.get(Outfit, task.outfit_id)
            if outfit and outfit.result_json.get("outfits"):
                idx = task.item_index or 0
                if idx < len(outfit.result_json["outfits"]):
                    items_text = build_items_text(outfit.result_json["outfits"][idx].get("items", {}))
        if not items_text:
            items_text = "基础百搭单品"

        prompt = render("image", ITEMS=items_text)
        save_path = settings.generated_dir / f"flatlay_{task_id}.png"
        saved = await llm_client.generate_image(prompt, save_path)

        task.status = "done"
        task.result_json = {"image_url": f"/static/generated/{saved.name}"}
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("平铺图任务失败: %s", e)
        try:
            task = db.get(Task, task_id)
            if task:
                task.status = "failed"
                task.error = "生成失败，请重试（不扣额度）"
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()
