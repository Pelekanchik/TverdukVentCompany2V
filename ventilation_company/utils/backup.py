"""Резервне копіювання бази даних VentCompany.

Автоматично створює .backup файли перед операціями, які можуть
пошкодити дані (міграції, масові оновлення).
"""

import os
import shutil
from datetime import datetime

from ventilation_company.utils.logging_config import get_logger

logger = get_logger("backup")


def create_backup(db_path: str = "data/company.db") -> str | None:
    """Створити резервну копію БД з timestamp.

    Повертає шлях до бекапу або None, якщо БД не існує.
    """
    if not os.path.exists(db_path):
        logger.warning("БД не знайдено для бекапу: %s", db_path)
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup.{timestamp}"

    try:
        shutil.copy2(db_path, backup_path)
        logger.info("✅ Бекап створено: %s", backup_path)
        return backup_path
    except Exception as e:
        logger.error("❌ Помилка створення бекапу: %s", e)
        return None


def list_backups(db_path: str = "data/company.db") -> list[str]:
    """Отримати список усіх бекапів БД."""
    db_dir = os.path.dirname(db_path) or "."
    db_name = os.path.basename(db_path)
    backups = []
    for f in os.listdir(db_dir):
        if f.startswith(db_name + ".backup."):
            backups.append(os.path.join(db_dir, f))
    backups.sort(reverse=True)  # найновіші спочатку
    return backups


def cleanup_old_backups(db_path: str = "data/company.db", keep: int = 10) -> int:
    """Видалити старі бекапи, залишивши `keep` найновіших.

    Повертає кількість видалених файлів.
    """
    backups = list_backups(db_path)
    to_delete = backups[keep:]
    deleted = 0
    for bp in to_delete:
        try:
            os.remove(bp)
            logger.info("🗑️ Видалено старий бекап: %s", os.path.basename(bp))
            deleted += 1
        except Exception as e:
            logger.warning("Не вдалося видалити %s: %s", bp, e)
    return deleted


def restore_backup(backup_path: str, db_path: str = "data/company.db") -> bool:
    """Відновити БД з резервної копії.

    Попередньо створює бекап поточної БД (якщо вона існує).
    """
    if not os.path.exists(backup_path):
        logger.error("Бекап не знайдено: %s", backup_path)
        return False

    # Бекап поточної перед відновленням
    if os.path.exists(db_path):
        create_backup(db_path)

    try:
        shutil.copy2(backup_path, db_path)
        logger.info("✅ БД відновлено з: %s", backup_path)
        return True
    except Exception as e:
        logger.error("❌ Помилка відновлення: %s", e)
        return False
