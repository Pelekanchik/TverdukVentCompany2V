#!/usr/bin/env python3
"""Застосувати всі міграції Alembic (upgrade to head)."""

import subprocess
import sys


def main():
    # Бекап перед міграціями
    from ventilation_company.utils.backup import create_backup, cleanup_old_backups
    from ventilation_company.utils.logging_config import setup_logging

    logger = setup_logging()
    backup_path = create_backup()
    if backup_path:
        cleanup_old_backups(keep=10)
        logger.info("🛡️ Бекап створено перед міграцією: %s", backup_path)

    cmd = ["alembic", "upgrade", "head"]
    print("=" * 50)
    print("⬆️  Застосування міграцій Alembic")
    print("=" * 50)
    print(f"Команда: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        logger.info("✅ Міграції успішно застосовано")
    else:
        logger.error("❌ Помилка міграцій (код: %s)", result.returncode)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
