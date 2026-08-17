#!/usr/bin/env python3
"""Створити нову міграцію Alembic (автогенерація з моделей)."""

import subprocess
import sys


def main():
    # Бекап перед створенням міграції
    from ventilation_company.utils.backup import create_backup, cleanup_old_backups
    from ventilation_company.utils.logging_config import setup_logging

    logger = setup_logging()
    backup_path = create_backup()
    if backup_path:
        cleanup_old_backups(keep=10)
        logger.info("🛡️ Бекап створено перед створенням міграції: %s", backup_path)

    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "auto"
    cmd = ["alembic", "revision", "--autogenerate", "-m", message]
    print("=" * 50)
    print("🔄 Створення міграції Alembic")
    print("=" * 50)
    print(f"Команда: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        logger.info("✅ Міграцію '%s' створено", message)
    else:
        logger.error("❌ Помилка створення міграції (код: %s)", result.returncode)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
