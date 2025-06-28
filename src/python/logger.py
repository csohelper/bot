import logging
from datetime import datetime
import os

def setup_logger(name: str = __name__) -> logging.Logger:
    if not os.path.exists("storage/logs"):
        os.makedirs("storage/logs", exist_ok=True)
    log_filename = f"storage/logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logging.getLogger('aiogram').setLevel(logging.INFO)
        logging.getLogger('aiogram').addHandler(console_handler)
        logging.getLogger('aiogram').addHandler(file_handler)

    return logger

logger = setup_logger()
