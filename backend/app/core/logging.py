"""日志：不记录密钥、密码、完整用户文档。"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("wearwise")
