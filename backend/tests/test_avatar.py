"""Avatar 与造型上身图测试（mock）。"""
import asyncio

from app.services import avatar_service


def _setup_garment_and_outfit(client, png_bytes):
    client.post("/api/v1/garments", files={"files": ("a.png", png_bytes, "image/png")})
    gid = client.get("/api/v1/garments").json()[0]["id"]
    client.patch(f"/api/v1/garments/{gid}", json={})
    import json
    r = client.post("/api/v1/outfits", json={"scene": "日常"})
    done_line = [l for l in r.text.split("\n") if l.startswith("data:")][-1]
    return json.loads(done_line[5:].strip())["outfit_id"]


def test_avatar_lifecycle(client, png_bytes):
    # 创建形象
    r = client.post("/api/v1/avatars", json={"height": "165cm", "build": "中等"})
    assert r.status_code == 201
    av_id = r.json()["id"]

    # 直接执行生成（避免后台任务时序）
    asyncio.run(avatar_service.process_avatar_task(av_id))

    av = client.get("/api/v1/avatars").json()[0]
    assert av["status"] == "done"
    assert len(av["candidates"]) == 4

    # 选为主形象
    r = client.post(f"/api/v1/avatars/{av_id}/select", json={"index": 1})
    assert r.status_code == 200
    assert r.json()["is_primary"] is True
    assert r.json()["selected"] == 1

    # 非法候选序号
    assert client.post(f"/api/v1/avatars/{av_id}/select", json={"index": 99}).status_code == 400


def test_avatar_outfit_image(client, png_bytes):
    outfit_id = _setup_garment_and_outfit(client, png_bytes)

    # 先生成并选择主形象
    av_id = client.post("/api/v1/avatars", json={}).json()["id"]
    asyncio.run(avatar_service.process_avatar_task(av_id))
    client.post(f"/api/v1/avatars/{av_id}/select", json={"index": 0})

    # 提交上身图任务
    r = client.post(f"/api/v1/outfits/{outfit_id}/items/0/avatar-image")
    assert r.status_code == 202
    task_id = r.json()["task_id"]

    asyncio.run(avatar_service.process_avatar_outfit_task(task_id))

    t = client.get(f"/api/v1/tasks/{task_id}").json()
    assert t["status"] == "done"
    assert t["result"]["image_url"].startswith("/static/generated/")


def test_avatar_outfit_requires_primary(client, png_bytes):
    # 清空已有主形象，保证本用例从"无主形象"状态开始
    from app.models.db import SessionLocal
    from app.models.entities import Avatar
    db = SessionLocal()
    db.query(Avatar).delete()
    db.commit()
    db.close()

    outfit_id = _setup_garment_and_outfit(client, png_bytes)
    r = client.post(f"/api/v1/outfits/{outfit_id}/items/0/avatar-image")
    task_id = r.json()["task_id"]
    asyncio.run(avatar_service.process_avatar_outfit_task(task_id))
    t = client.get(f"/api/v1/tasks/{task_id}").json()
    assert t["status"] == "failed"
    assert "数字形象" in t["error"]
