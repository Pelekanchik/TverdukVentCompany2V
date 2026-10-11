"""Хмарне резервне копіювання VentCompany.

Два канали (незалежні, можуть працювати разом):

1. Telegram Bot API — дамп надсилається файлом у чат через HTTPS
   (тільки стандартна бібліотека Python, жодних залежностей).
   Ліміт Telegram — 50 МБ на файл.
2. Хмарні теки синхронізації (OneDrive / Google Drive / Dropbox / Яндекс.Диск) —
   якщо на ПК встановлено клієнта, дамп копіюється у підтеку
   `VentCompanyBackups` і клієнт синхронізує його сам.

У разі будь-якої помилки пише у лог і повертає помилку у результаті —
хмарний бекап ніколи не ламає локальний автобекап чи старт програми.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from urllib import parse as urlparse
from urllib import request as urlrequest

from ventilation_company.utils.logging_config import get_logger

logger = get_logger("cloud_backup")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendDocument"
TELEGRAM_MESSAGE_API = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_MAX_BYTES = 50 * 1024 * 1024  # ліміт Bot API на файл


def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Надіслати текстове повідомлення у Telegram-чат (sendMessage).

    Повертає True при HTTP 200. Винятки не підіймає — лише лог + False.
    """
    body = urlparse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urlrequest.Request(
        TELEGRAM_MESSAGE_API.format(token=token),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except Exception as exc:  # noqa: BLE001 — мережа недоступна, токен невалідний тощо
        logger.error("Telegram message failed: %s", exc)
        return False


# Типові місця хмарних тек на Windows (відносно профілю користувача).
CLOUD_FOLDER_CANDIDATES = (
    ("OneDrive", "OneDrive"),
    ("Google Drive", "Google Drive"),
    ("Google Drive", "My Drive"),
    ("Dropbox", "Dropbox"),
    ("Яндекс.Диск", "Яндекс.Диск"),
    ("Яндекс.Диск", "Yandex.Disk"),
)

CLOUD_SUBFOLDER = "VentCompanyBackups"


def detect_cloud_folders() -> list[tuple[str, str]]:
    """Знайти встановлені хмарні теки синхронізації.

    Повертає список (назва, шлях) для існуючих тек; дублікати виключено.
    """
    home = Path.home()
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, folder in CLOUD_FOLDER_CANDIDATES:
        candidate = home / folder
        key = str(candidate).lower()
        if candidate.is_dir() and key not in seen:
            found.append((name, str(candidate)))
            seen.add(key)
    return found


def send_telegram_document(token: str, chat_id: str, file_path: str, caption: str = "") -> bool:
    """Надіслати файл у Telegram-чат через Bot API (multipart/form-data).

    Повертає True при HTTP 200. Винятки не підіймає — лише лог + False.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.error("Telegram: файл не знайдено: %s", file_path)
        return False
    size = path.stat().st_size
    if size > TELEGRAM_MAX_BYTES:
        logger.error(
            "Telegram: файл занадто великий (%d байт > %d) — пропущено",
            size,
            TELEGRAM_MAX_BYTES,
        )
        return False

    boundary = uuid.uuid4().hex
    file_bytes = path.read_bytes()
    body = b""
    for field, value in (("chat_id", chat_id), ("caption", caption)):
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; '
        f'filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body += file_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urlrequest.Request(
        TELEGRAM_API.format(token=token),
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            ok = resp.status == 200
    except Exception as exc:  # noqa: BLE001 — мережа недоступна, токен невалідний тощо
        logger.error("Telegram upload failed: %s", exc)
        return False
    if ok:
        logger.info("Telegram: надіслано %s (%d байт)", path.name, size)
    return ok


def copy_to_cloud_folders(backup_path: str) -> list[str]:
    """Скопіювати дамп у підтеку VentCompanyBackups у кожній знайденій хмарній теці.

    Повертає список шляхів призначення. Помилки копіювання — лише у лог.
    """
    copied: list[str] = []
    for _name, folder in detect_cloud_folders():
        dest_dir = Path(folder) / CLOUD_SUBFOLDER
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / Path(backup_path).name
            shutil.copy2(backup_path, dest)
            copied.append(str(dest))
            logger.info("Хмарна тека: скопійовано у %s", dest)
        except Exception as exc:  # noqa: BLE001 — одна тека недоступна ≠ відміна решти
            logger.warning("Не вдалося скопіювати у %s: %s", dest_dir, exc)
    return copied


def cleanup_cloud_folders(keep: int = 7) -> int:
    """Ротація у хмарних теках: лишити `keep` найновіших дампів у кожній теці.

    Повертає кількість видалених файлів.
    """
    deleted = 0
    for _name, folder in detect_cloud_folders():
        dest_dir = Path(folder) / CLOUD_SUBFOLDER
        if not dest_dir.is_dir():
            continue
        dumps = sorted(dest_dir.glob("*.dump"), key=lambda p: p.name, reverse=True)
        for old in dumps[keep:]:
            try:
                old.unlink()
                deleted += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не вдалося видалити %s: %s", old, exc)
    return deleted


def cloud_backup_preferences() -> tuple[bool, str, str]:
    """Налаштування хмарного бекапу з БД: (enabled, telegram_token, telegram_chat)."""
    enabled, token, chat = False, "", ""
    try:
        from ventilation_company.database.repositories.app_settings_repository import (
            AppSettingsRepository,
        )

        repo = AppSettingsRepository()
        enabled = repo.get("app.cloud_backup_enabled", "0") == "1"
        token = repo.get("app.cloud_backup_telegram_token", "").strip()
        chat = repo.get("app.cloud_backup_telegram_chat", "").strip()
    except Exception as exc:  # noqa: BLE001 — дефолти при недоступній БД
        logger.warning("Cloud backup preferences unreadable, using defaults: %s", exc)
    return enabled, token, chat


def build_backup_report(backup_path: str) -> str:
    """Створити читабельний TXT-звіт до дампу (дата, розмір, статистика БД).

    Звіт кладеться поруч із дампом з тим самим штампом часу
    (`ventcompany_<штамп>_звіт.txt`). Помилки читання БД лише логуються —
    звіт завжди містить хоча б дату й розмір дампу. Повертає шлях до звіту.
    """
    path = Path(backup_path)
    stamp = path.stem.removeprefix("ventcompany_")
    report_path = path.with_name(f"ventcompany_{stamp}_звіт.txt")
    size_mb = path.stat().st_size / (1024 * 1024)

    lines = [
        "VentCompany — звіт до резервної копії",
        "=" * 40,
        f"Дата створення копії: {datetime.now():%d.%m.%Y %H:%M}",
        f"Файл копії: {path.name}",
        f"Розмір копії: {size_mb:.2f} МБ",
    ]
    try:
        from ventilation_company.version import __version__

        lines.append(f"Версія програми: {__version__}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Версія програми недоступна: %s", exc)
    lines.append("")

    try:
        lines.extend(_collect_backup_stats())
    except Exception as exc:  # noqa: BLE001 — звіт не повинен ламати бекап
        logger.warning("Статистика БД для звіту недоступна: %s", exc)
        lines.append("Статистика БД: недоступна (див. логи програми).")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Створено звіт до бекапу: %s", report_path)
    return str(report_path)


def _collect_backup_stats() -> list[str]:
    """Підсумки з БД для звіту: проєкти, клієнти, оплати, дебіторка."""
    from ventilation_company.database.repositories.client_repo import ClientRepository
    from ventilation_company.database.repositories.project_repo import ProjectRepository
    from ventilation_company.services.receivables import (
        _DONE_STATUSES,
        build_receivables,
        receivables_totals,
    )

    projects = ProjectRepository.list_all()
    totals = receivables_totals(build_receivables(projects))
    active = [p for p in projects if (p.get("status") or "").strip().lower() not in _DONE_STATUSES]
    clients = ClientRepository.list_all()

    def _fmt(amount: float) -> str:
        return f"{amount:,.2f}".replace(",", " ")

    return [
        "Статистика бази даних",
        "-" * 40,
        f"Проєктів усього: {len(projects)}",
        f"Активних проєктів: {len(active)}",
        f"Клієнтів: {len(clients)}",
        f"Договірна вартість проєктів: {_fmt(totals['total'])} грн",
        f"Отримано оплат: {_fmt(totals['paid'])} грн",
        f"Дебіторська заборгованість: {_fmt(totals['debt'])} грн",
        f"Передоплати (переплати): {_fmt(totals['overpaid'])} грн",
    ]


def upload_backup(backup_path: str, token: str = "", chat: str = "") -> dict:
    """Відправити готовий дамп у хмару (Telegram і/або хмарні теки).

    У Telegram разом із дампом надсилається читабельний TXT-звіт
    (дата, розмір, кількість проєктів/клієнтів, дебіторка).
    Повертає {"telegram": bool|None, "folders": [шляхи]}. Ніколи не підіймає
    винятки — хмарний бекап не повинен ламати автобекап.
    """
    result: dict = {"telegram": None, "folders": []}
    if not backup_path or not Path(backup_path).is_file():
        return result
    if token and chat:
        try:
            caption = f"VentCompany backup: {Path(backup_path).name}"
            result["telegram"] = send_telegram_document(token, chat, backup_path, caption)
            if result["telegram"]:
                report_path = ""
                try:
                    report_path = build_backup_report(backup_path)
                    send_telegram_document(
                        token, chat, report_path, "Звіт до резервної копії VentCompany"
                    )
                except Exception as exc:  # noqa: BLE001 — звіт необов'язковий
                    logger.error("Telegram report upload skipped: %s", exc)
                finally:
                    if report_path:
                        try:
                            Path(report_path).unlink(missing_ok=True)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Не вдалося видалити звіт %s: %s", report_path, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Telegram upload skipped: %s", exc)
            result["telegram"] = False
    try:
        result["folders"] = copy_to_cloud_folders(backup_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cloud folder copy skipped: %s", exc)
    return result


def summary_json(result: dict) -> str:
    """Серіалізований підсумок для аудиту/логів."""
    return json.dumps(result, ensure_ascii=False)
