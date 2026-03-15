import logging
import os
from datetime import datetime

class Log:

    logger = logging.getLogger("app_logger")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
    )

    # ===== Console =====
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # ===== Pasta de logs =====
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # ===== Nome do arquivo com data =====
    hoje = datetime.now().strftime("%d_%m_%Y")
    log_file = f"logs/{hoje}.log"

    # ===== Handler de arquivo =====
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    @staticmethod
    def info(msg: str):
        Log.logger.info(msg, stacklevel=2)

    @staticmethod
    def warning(msg: str):
        Log.logger.warning(msg, stacklevel=2)

    @staticmethod
    def error(msg: str):
        Log.logger.error(msg, stacklevel=2)

    @staticmethod
    def debug(msg: str):
        Log.logger.debug(msg, stacklevel=2)

    @staticmethod
    def critical(msg: str):
        Log.logger.critical(msg, stacklevel=2)