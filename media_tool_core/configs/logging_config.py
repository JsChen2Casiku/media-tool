import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from media_tool_core.configs.general_constants import LOG_PATH

log_path = Path(LOG_PATH) / "media_tool.log"
log_path.parent.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        RotatingFileHandler(str(log_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("media_tool")


def get_logger(name):
    return logging.getLogger(name)
