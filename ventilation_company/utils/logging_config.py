"""Налаштування логування для VentCompany.

Рівні логування:
  DEBUG   — детальна інформація для розробки
  INFO    — загальні події (запуск, збереження)
  WARNING — попередження (не критичні помилки)
  ERROR   — помилки, які потребують уваги
  CRITICAL — критичні помилки (втрата даних)
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "ventcompany.log")
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5  # зберігати 5 старих файлів


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Налаштувати логування для VentCompany.

    Повертає кореневий логер, який пише:
      • в консоль (INFO+)
      • в файл (DEBUG+)
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("ventcompany")
    logger.setLevel(logging.DEBUG)

    # Уникнути дублювання хендлерів при повторному виклику
    if logger.handlers:
        return logger

    # Формат повідомлень
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # ── Консоль ──────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Файл (ротація) ──────────────────────────────────────
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Логування налаштовано | рівень: %s", logging.getLevelName(level))
    return logger


def get_logger(name: str) -> logging.Logger:
    """Отримати логер для конкретного модуля."""
    return logging.getLogger(f"ventcompany.{name}")
