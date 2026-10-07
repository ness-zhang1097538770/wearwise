"""API 集成测试：状态流转、错误路径、SSE 收尾、成像任务（mock）。"""
import asyncio

from app.models.db import SessionLocal
from app.models.entities import Outfit, Task
from app.services import imaging


def _upload(client, png_bytes, name="a.png"):
    return client.post(
        "/api/v1/garments",
        files={"files": (name, png_bytes, "image/png")},
    )


def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_garment_lifecycle(client, png_bytes):
    # 上传 + 识别（mock 返回固定标签）
    r = _upload(client, png_bytes)
    assert r.status_code == 201, r.text
    g = r.json()[0]  # 批量上传返回列表
    assert g["status"] == "draft"
    assert g["category"] == "上装"  # mock 固定值

    # 修正 → confirmed
    r = client.patch(f"/api/v1/garments/{g['id']}", json={"color": "藏青"})
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"
    assert r.json()["color"] == "藏青"

    # 列表
    assert len(client.get("/api/v1/garments").json()) == 1

    # 删除
    assert client.delete(f"/api/v1/garments/{g['id']}").status_code == 204
    assert client.patch(f"/api/v1/garments/{g['id']}", json={}).status_code == 404


def test_garment_not_found(client):
    assert client.patch("/api/v1/garments/999", json={}).status_code == 404


def test_outfit_requires_confirmed_garment(client):
    r = client.post("/api/v1/outfits", json={"scene": "日常"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "no_garments"


def test_outfit_sse_done(client, png_bytes):
    _upload(client, png_bytes)
    # 确认一件衣物
    gid = client.get("/api/v1/garments").json()[0]["id"]
    client.patch(f"/api/v1/garments/{gid}", json={})

    r = client.post("/api/v1/outfits", json={"scene": "日常通勤"})
    assert r.status_code == 200
    body = r.text
    assert "event: chunk" in body
    assert "event: done" in body
    # 3 套方案
    import json
    done_line = [l for l in body.split("\n") if l.startswith("data:")][-1]
    data = json.loads(done_line[5:].strip())
    assert len(data["outfits"]) == 3


def test_outfit_favorite_and_image(client, png_bytes):
    _upload(client, png_bytes)
    gid = client.get("/api/v1/garments").json()[0]["id"]
    client.patch(f"/api/v1/garments/{gid}", json={})
    r = client.post("/api/v1/outfits", json={"scene": "日常"})
    import json
    done_line = [l for l in r.text.split("\n") if l.startswith("data:")][-1]
    outfit_id = json.loads(done_line[5:].strip())["outfit_id"]

    # 收藏
    fav = client.post(f"/api/v1/outfits/{outfit_id}/favorite").json()
    assert fav["favorite"] is True

    # 提交平铺图任务
    r = client.post(f"/api/v1/outfits/{outfit_id}/items/0/image")
    assert r.status_code == 202
    task_id = r.json()["task_id"]

    # 直接执行后台任务（避免依赖 TestClient 的后台任务时序）
    asyncio.run(imaging.process_image_task(task_id))

    t = client.get(f"/api/v1/tasks/{task_id}").json()
    assert t["status"] == "done"
    assert t["result"]["image_url"].startswith("/static/generated/")


def test_error_structure(client):
    r = client.get("/api/v1/tasks/999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert "message" in r.json()["error"]
