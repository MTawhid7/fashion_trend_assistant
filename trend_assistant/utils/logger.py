"""
Configures a centralized logger for the application.
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
from .. import config

LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

config.LOGS_DIR.mkdir(exist_ok=True)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

file_handler = RotatingFileHandler(
    filename=config.LOG_FILE_PATH, maxBytes=1024 * 1024, backupCount=3
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

logger = logging.getLogger("trend_assistant")
logger.setLevel(logging.INFO)

if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
