"""Avatar 数字形象与造型上身图服务。"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import logger
from app.models.db import SessionLocal
from app.models.entities import Avatar, Outfit, Task
from app.services import llm_client
from app.services.prompts import render

settings = get_settings()


def build_avatar_params_text(params: dict) -> str:
    parts = []
    labels = {"height": "身高", "build": "体型", "skin": "肤色", "hair": "发色发型", "age": "年龄"}
    for k, label in labels.items():
        v = (params or {}).get(k, "").strip()
        if v:
            parts.append(f"{label}：{v}")
    if not parts:
        parts = ["身高：165cm", "体型：中等", "肤色：自然肤色", "发色发型：黑色", "年龄：25-30岁"]
    return "，".join(parts)


def _local_path(url: str) -> str:
    return str(settings.generated_dir / url.split("/")[-1])


def _primary_avatar_path(db) -> str | None:
    av = db.query(Avatar).filter(Avatar.is_primary == 1, Avatar.status == "done").first()
    if av is None or av.selected is None or not av.candidates_json:
        return None
    for c in av.candidates_json:
        if c.get("index") == av.selected:
            return _local_path(c["image_url"])
    return None


def _candidate_path(av: Avatar, index: int) -> str | None:
    for c in av.candidates_json or []:
        if c.get("index") == index:
            return _local_path(c["image_url"])
    return None


async def process_avatar_fuse_task(task_id: int) -> None:
    """融合两张候选（脸 + 身材）生成新形象，追加为新的候选。"""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        ctx = task.result_json or {}
        av = db.get(Avatar, ctx.get("avatar_id"))
        if av is None:
            task.status = "failed"
            task.error = "形象不存在"
            db.commit()
            return
        face_path = _candidate_path(av, ctx.get("face_index"))
        body_path = _candidate_path(av, ctx.get("body_index"))
        if not face_path or not body_path:
            task.status = "failed"
            task.error = "候选图片不存在"
            db.commit()
            return

        # 第一步：先高清锐化脸部特写（脸占画面大，眼睛更清晰）
        face_sharp = await llm_client.generate_image(
            render("avatar_facesharp"),
            settings.generated_dir / f"avatar_face_{task_id}.png",
            reference_paths=[face_path],
        )
        # 第二步：用高清脸 + 身材参考图融合
        prompt = render("avatar_fuse")
        saved = await llm_client.generate_image(
            prompt,
            settings.generated_dir / f"avatar_fuse_{task_id}.png",
            reference_paths=[str(face_sharp), body_path],
        )
        # 追加为新候选
        new_index = len(av.candidates_json or [])
        av.candidates_json = (av.candidates_json or []) + [
            {"index": new_index, "image_url": f"/static/generated/{saved.name}"}
        ]
        db.commit()
        task.status = "done"
        task.result_json = {"image_url": f"/static/generated/{saved.name}", "new_index": new_index}
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("Avatar 融合失败: %s", e)
        try:
            task = db.get(Task, task_id)
            if task:
                task.status = "failed"
                task.error = "融合失败，请重试"
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


async def process_avatar_task(avatar_id: int) -> None:
    """生成 4 个 Avatar 候选形象。"""
    db = SessionLocal()
    try:
        av = db.get(Avatar, avatar_id)
        if av is None:
            return
        av.status = "running"
        db.commit()

        prompt = render("avatar", PARAMS=build_avatar_params_text(av.params_json))
        paths = await llm_client.generate_images(
            prompt, settings.generated_dir, f"avatar_{avatar_id}", num=4
        )
        av.candidates_json = [
            {"index": i, "image_url": f"/static/generated/{p.name}"} for i, p in enumerate(paths)
        ]
        av.status = "done"
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("Avatar 生成失败: %s", e)
        try:
            av = db.get(Avatar, avatar_id)
            if av:
                av.status = "failed"
                av.error = "生成失败，请重试"
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


async def process_avatar_outfit_task(task_id: int) -> None:
    """用主形象作参考图，生成造型上身图。"""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        ref_path = _primary_avatar_path(db)
        if ref_path is None:
            task.status = "failed"
            task.error = "请先生成并选择数字形象（Avatar）"
            db.commit()
            return

        items_text = "基础百搭单品"
        if task.outfit_id is not None:
            outfit = db.get(Outfit, task.outfit_id)
            if outfit and outfit.result_json.get("outfits"):
                idx = task.item_index or 0
                if idx < len(outfit.result_json["outfits"]):
                    items_text = "；".join(
                        f"{k}：{v}" for k, v in outfit.result_json["outfits"][idx].get("items", {}).items() if v
                    )

        prompt = render("avatar_outfit", ITEMS=items_text)
        saved = await llm_client.generate_image(
            prompt,
            settings.generated_dir / f"avatar_outfit_{task_id}.png",
            reference_paths=[ref_path],
        )
        task.status = "done"
        task.result_json = {"image_url": f"/static/generated/{saved.name}"}
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("造型上身图生成失败: %s", e)
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
