"""Резервне копіювання VentCompany.

PostgreSQL — через pg_dump/pg_restore.
SQLite — залишено тільки для dev/legacy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from ventilation_company.utils.logging_config import get_logger

logger = get_logger("backup")

DEFAULT_SQLITE_DB = "data/company.db"
DEFAULT_BACKUP_DIR = "backups"

# JSON-файли з цінами/реквізитами — копіюються поруч із dump (той самий штамп часу).
SETTINGS_FILES = ("pricing_settings.json", "business_settings.json")


def _settings_data_dir() -> Path:
    """Тека з JSON-налаштуваннями (винесено для тестованості)."""
    from ventilation_company.paths import DATA_DIR

    return DATA_DIR


def _copy_settings(out_dir: Path, stamp: str) -> None:
    """Скопіювати JSON-налаштування у теку бекапів із загальним штампом."""
    for name in SETTINGS_FILES:
        src = _settings_data_dir() / name
        if src.exists():
            shutil.copy2(src, out_dir / f"ventcompany_{stamp}_settings_{name}")


def _database_url() -> str:
    from ventilation_company.database.db import DATABASE_URL

    return DATABASE_URL


def _find_pg_tool(name: str) -> str | None:
    """Знайти pg_dump/pg_restore: спочатку PATH, потім типові теки Windows.

    Інсталятор PostgreSQL не додає bin\\ у PATH, тому на чистих ПК
    інструменти недоступні за ім'ям — шукаємо їх самі.
    """
    from shutil import which

    found = which(name)
    if found:
        return found
    prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pg_dir = Path(prog_files) / "PostgreSQL"
    if pg_dir.is_dir():
        for version_dir in sorted(pg_dir.iterdir(), reverse=True):
            candidate = version_dir / "bin" / f"{name}.exe"
            if candidate.exists():
                return str(candidate)
    return None


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql://") or url.startswith("postgres://")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _run_pg_tool(args: list[str], url: str) -> subprocess.CompletedProcess:
    parsed = urlparse(url)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    tool = _find_pg_tool(args[0])
    if tool is None:
        raise FileNotFoundError(
            f"Інструмент {args[0]} не знайдено ні в PATH, ні у {os.environ.get('PROGRAMFILES')}\\PostgreSQL"
        )

    base = [
        "-h",
        parsed.hostname or "localhost",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "postgres",
    ]
    return subprocess.run(
        [tool, *base, *args[1:]],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def create_backup(
    db_path: str = DEFAULT_SQLITE_DB, backup_dir: str = DEFAULT_BACKUP_DIR
) -> str | None:
    """Створити backup поточної БД.

    Для PostgreSQL створює custom-format dump у `backup_dir`.
    Для SQLite копіює файл БД поруч із ним.
    """
    url = _database_url()

    if _is_postgres(url):
        out_dir = Path(backup_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = _timestamp()
        backup_path = out_dir / f"ventcompany_{stamp}.dump"

        try:
            result = _run_pg_tool(
                [
                    "pg_dump",
                    "-d",
                    urlparse(url).path.lstrip("/"),
                    "-F",
                    "c",
                    "-f",
                    str(backup_path),
                ],
                url,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.error("pg_dump unavailable: %s", exc)
            return None
        if result.returncode != 0:
            logger.error("pg_dump failed: %s", result.stderr)
            return None
        _copy_settings(out_dir, stamp)
        logger.info("PostgreSQL backup created: %s", backup_path)
        return str(backup_path)

    if not os.path.exists(db_path):
        logger.warning("Database not found for backup: %s", db_path)
        return None

    sqlite_backup_path = f"{db_path}.backup.{_timestamp()}"
    try:
        shutil.copy2(db_path, sqlite_backup_path)
        logger.info("SQLite backup created: %s", sqlite_backup_path)
        return sqlite_backup_path
    except Exception as e:
        logger.error("Backup failed: %s", e)
        return None


def list_backups(
    db_path: str = DEFAULT_SQLITE_DB, backup_dir: str = DEFAULT_BACKUP_DIR
) -> list[str]:
    """Список backup-файлів, найновіші першими."""
    url = _database_url()
    if _is_postgres(url):
        out_dir = Path(backup_dir)
        if not out_dir.is_dir():
            return []
        files = [str(p) for p in out_dir.glob("*.dump")]
        files += [str(p) for p in out_dir.glob("ventcompany_*_settings_*.json")]
        files.sort(reverse=True)
        return files

    db_dir = os.path.dirname(db_path) or "."
    if not os.path.isdir(db_dir):
        return []
    db_name = os.path.basename(db_path)
    backups = []
    for f in os.listdir(db_dir):
        if f.startswith(db_name + ".backup."):
            backups.append(os.path.join(db_dir, f))
    backups.sort(reverse=True)
    return backups


def cleanup_old_backups(
    db_path: str = DEFAULT_SQLITE_DB,
    backup_dir: str = DEFAULT_BACKUP_DIR,
    keep: int = 10,
) -> int:
    """Видалити старі backups, залишивши `keep` найновіших комплектів.

    Комплект = dump + JSON-копії налаштувань з тим самим штампом часу.
    """
    url = _database_url()
    deleted = 0

    if _is_postgres(url):
        out_dir = Path(backup_dir)
        if not out_dir.is_dir():
            return 0
        stamps = sorted(
            {p.name[len("ventcompany_") : -len(".dump")] for p in out_dir.glob("*.dump")},
            reverse=True,
        )
        for stamp in stamps[keep:]:
            candidates = [
                out_dir / f"ventcompany_{stamp}.dump",
                *out_dir.glob(f"ventcompany_{stamp}_settings_*.json"),
            ]
            for path in candidates:
                try:
                    os.remove(path)
                    logger.info("Deleted old backup: %s", path)
                    deleted += 1
                except Exception as e:
                    logger.warning("Cannot delete %s: %s", path, e)
        return deleted

    backups = list_backups(db_path=db_path, backup_dir=backup_dir)
    for old_path in backups[keep:]:
        try:
            os.remove(old_path)
            logger.info("Deleted old backup: %s", old_path)
            deleted += 1
        except Exception as e:
            logger.warning("Cannot delete %s: %s", old_path, e)
    return deleted


def auto_backup_on_start(backup_dir: str | None = None, keep: int = 7) -> str | None:
    """Автобекап при запуску програми (dump БД + JSON-налаштування, ротація).

    Виконується у фоновому потоці з launch_gui: ніколи не піднімає винятки —
    у разі помилки лише пише у лог і повертає None, щоб не блокувати старт.
    """
    if backup_dir is None:
        from ventilation_company.bootstrap import BACKUP_DIR

        backup_dir = str(BACKUP_DIR)
    try:
        path = create_backup(backup_dir=backup_dir)
    except Exception as exc:  # noqa: BLE001 — автобекап не повинен ламати старт
        logger.warning("Auto backup skipped: %s", exc)
        return None
    try:
        cleanup_old_backups(backup_dir=backup_dir, keep=keep)
    except Exception as exc:  # noqa: BLE001 — ротація некритична
        logger.warning("Backup rotation skipped: %s", exc)
    return path


def restore_backup(backup_path: str, db_path: str = DEFAULT_SQLITE_DB) -> bool:
    """Відновити БД з backup.

    Перед restore створює backup поточної БД.
    """
    if not os.path.exists(backup_path):
        logger.error("Backup not found: %s", backup_path)
        return False

    url = _database_url()

    if _is_postgres(url):
        create_backup(backup_dir=DEFAULT_BACKUP_DIR)
        result = _run_pg_tool(
            ["pg_restore", "-d", urlparse(url).path.lstrip("/"), "-c", backup_path],
            url,
        )
        if result.returncode != 0:
            logger.error("pg_restore failed: %s", result.stderr)
            return False
        logger.info("PostgreSQL restored from: %s", backup_path)
        return True

    if os.path.exists(db_path):
        create_backup(db_path)
    try:
        shutil.copy2(backup_path, db_path)
        logger.info("SQLite restored from: %s", backup_path)
        return True
    except Exception as e:
        logger.error("Restore failed: %s", e)
        return False


if __name__ == "__main__":
    path = create_backup()
    if path:
        print(path)
