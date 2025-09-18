import logging
from datetime import datetime
import os
from .storage.config import config


def setup_logger(name: str = __name__) -> logging.Logger:
    if not os.path.exists("storage/logs"):
        os.makedirs("storage/logs", exist_ok=True)
    log_filename = f"storage/logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    logger = logging.getLogger(name)

    # Базовый уровень — самый низкий, чтобы не отбрасывать сообщения
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Преобразуем строки уровней в числовые значения
        console_level = getattr(logging, config.logger.console_level.upper(), logging.INFO)
        file_level = getattr(logging, config.logger.file_level.upper(), logging.DEBUG)
        aiogram_level = getattr(logging, config.logger.aiogram_level.upper(), logging.INFO)

        # Хендлер для файла
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level)

        # Хендлер для консоли
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(console_level)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Настройки для aiogram
        aiogram_logger = logging.getLogger('aiogram')
        aiogram_logger.setLevel(aiogram_level)
        aiogram_logger.addHandler(console_handler)
        aiogram_logger.addHandler(file_handler)

    return logger


logger = setup_logger()
