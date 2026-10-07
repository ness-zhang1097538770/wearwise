"""购物分析测试（mock）。"""
import asyncio

from app.services import analysis_service


def test_parse_analysis_report():
    raw = '{"match_score":80,"duplicate_score":10,"similar_items":["a"],"can_pair_count":5,"cost_per_wear":"约 3 元/次","suggestion":"值得考虑"}'
    r = analysis_service.parse_analysis_report(raw)
    assert r["match_score"] == 80
    assert r["duplicate_score"] == 10
    assert r["suggestion"] == "值得考虑"


def test_parse_analysis_report_empty():
    r = analysis_service.parse_analysis_report("")
    assert r["match_score"] == 0
    assert r["suggestion"] == "建议等待"


def test_analysis_api(client, png_bytes):
    # 先有衣柜
    client.post("/api/v1/garments", files={"files": ("a.png", png_bytes, "image/png")})
    gid = client.get("/api/v1/garments").json()[0]["id"]
    client.patch(f"/api/v1/garments/{gid}", json={})

    r = client.post("/api/v1/analysis", files={"file": ("p.png", png_bytes, "image/png")})
    assert r.status_code == 200
    body = r.text
    assert "event: chunk" in body
    assert "event: done" in body

    # 历史列表
    hist = client.get("/api/v1/analysis").json()
    assert len(hist) == 1
    assert "match_score" in hist[0]["report"]
