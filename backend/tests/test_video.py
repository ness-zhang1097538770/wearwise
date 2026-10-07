"""视频任务测试（mock）。"""
import asyncio

from app.services import avatar_service, video_service


def _setup(client, png_bytes):
    client.post("/api/v1/garments", files={"files": ("a.png", png_bytes, "image/png")})
    gid = client.get("/api/v1/garments").json()[0]["id"]
    client.patch(f"/api/v1/garments/{gid}", json={})
    import json
    r = client.post("/api/v1/outfits", json={"scene": "日常"})
    done_line = [l for l in r.text.split("\n") if l.startswith("data:")][-1]
    return json.loads(done_line[5:].strip())["outfit_id"]


def test_video_requires_avatar_image(client, png_bytes):
    outfit_id = _setup(client, png_bytes)
    r = client.post(f"/api/v1/outfits/{outfit_id}/items/0/video")
    assert r.status_code == 202
    task_id = r.json()["task_id"]
    asyncio.run(video_service.process_video_task(task_id))
    t = client.get(f"/api/v1/tasks/{task_id}").json()
    assert t["status"] == "failed"
    assert "上身图" in t["error"]


def test_video_with_avatar_image(client, png_bytes):
    outfit_id = _setup(client, png_bytes)
    # 先生成主形象 + 上身图
    av_id = client.post("/api/v1/avatars", json={}).json()["id"]
    asyncio.run(avatar_service.process_avatar_task(av_id))
    client.post(f"/api/v1/avatars/{av_id}/select", json={"index": 0})
    r = client.post(f"/api/v1/outfits/{outfit_id}/items/0/avatar-image")
    atid = r.json()["task_id"]
    asyncio.run(avatar_service.process_avatar_outfit_task(atid))

    # 提交视频任务（mock 直接 done）
    r = client.post(f"/api/v1/outfits/{outfit_id}/items/0/video")
    task_id = r.json()["task_id"]
    asyncio.run(video_service.process_video_task(task_id))
    t = client.get(f"/api/v1/tasks/{task_id}").json()
    assert t["status"] == "done"
