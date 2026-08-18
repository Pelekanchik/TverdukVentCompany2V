"""Проста конфігурація логування."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Налаштувати базове логування для додатку.

    Returns:
        Кореневий логер.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    return logging.getLogger()


def get_logger(name: str) -> logging.Logger:
    """Отримати логер з базовою конфігурацією."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
    return logger
