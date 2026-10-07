"""测试配置：隔离数据目录 + mock 模型，离线可跑。"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="wearwise_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOADS_DIR"] = f"{_tmp}/uploads"
os.environ["GENERATED_DIR"] = f"{_tmp}/generated"
os.environ["MOCK_LLM"] = "true"
os.environ["ARK_API_KEY"] = ""
os.environ["ENABLE_CUTOUT"] = "false"  # 测试跳过 rembg 抠图（避免模型下载）

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_db():
    """每个测试前清空数据库，保证隔离。"""
    from app.models.db import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def png_bytes():
    from app.services.llm_client import make_placeholder_png
    from pathlib import Path
    p = Path(_tmp) / "sample.png"
    make_placeholder_png(p, 10, 10)
    return p.read_bytes()
