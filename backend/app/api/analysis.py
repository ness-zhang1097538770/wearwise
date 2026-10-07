"""购物防冲动分析接口：上传商品图 → SSE 流式返回报告。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.errors import error_body
from app.models.db import SessionLocal, get_db
from app.models.entities import Analysis, Garment
from app.services import analysis_service, files

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
async def create_analysis(file: UploadFile = File(...), db: Session = Depends(get_db)):
    path = await files.save_upload(file)
    garments = [g.to_dict() for g in db.query(Garment).filter(Garment.status == "confirmed").all()]

    async def gen():
        try:
            yield _sse("chunk", {"text": "正在识别商品信息…"})
            result = await analysis_service.analyze(str(path), garments)
            s = SessionLocal()
            try:
                a = Analysis(product_json=result["product"], report_json=result["report"], image_path=str(path))
                s.add(a)
                s.commit()
                s.refresh(a)
                analysis_id = a.id
            finally:
                s.close()
            yield _sse("chunk", {"text": "分析完成"})
            yield _sse("done", {"analysis_id": analysis_id, **result})
        except Exception as e:  # noqa: BLE001
            yield _sse("error", error_body("analysis_failed", "分析失败，请重试"))

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("")
def list_analyses(db: Session = Depends(get_db)):
    return [a.to_dict() for a in db.query(Analysis).order_by(Analysis.created_at.desc()).all()]
