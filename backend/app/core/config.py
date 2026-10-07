"""应用配置：从 .env 读取，密钥不回显、不进仓库。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_DIR = BASE_DIR.parent  # docs/wearwise穿衣助手/
DATA_DIR = PROJECT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "WearWise"
    api_prefix: str = "/api/v1"

    # 数据与文件目录
    database_url: str = f"sqlite:///{DATA_DIR / 'wardrobe.db'}"
    uploads_dir: Path = DATA_DIR / "uploads"
    generated_dir: Path = DATA_DIR / "generated"

    # 火山方舟模型
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    vision_model: str = "doubao-1.5-vision-pro"
    text_model: str = "doubao-1.5-pro-32k"
    image_model: str = "seedream-3.0-t2i"
    video_model: str = ""

    # 行为
    mock_llm: bool = True
    enable_cutout: bool = True  # 是否启用 rembg 本地抠图
    request_timeout: int = 60
    max_upload_mb: int = 20

    @property
    def use_mock(self) -> bool:
        """无 Key 或显式 mock 时，一律走 mock（不调用真实模型）。"""
        return self.mock_llm or not self.ark_api_key


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    s.generated_dir.mkdir(parents=True, exist_ok=True)
    return s
