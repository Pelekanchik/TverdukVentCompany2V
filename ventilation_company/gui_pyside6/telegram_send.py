"""Відправка документів у Telegram з GUI (фоновий потік + діалог результату).

Повторно використовує бота та chat_id з налаштувань хмарного бекапу
(Налаштування → Резервні копії → Telegram).
"""

from __future__ import annotations

import os
from contextlib import suppress

from PySide6.QtWidgets import QMessageBox

from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.utils.cloud_backup import (
    cloud_backup_preferences,
    send_telegram_document,
)


def telegram_prefs_or_warn(parent) -> tuple[str, str] | None:
    """(token, chat_id), якщо бот налаштовано; інакше None + попередження."""
    _enabled, token, chat = cloud_backup_preferences()
    if not token or not chat:
        QMessageBox.warning(
            parent,
            "Telegram",
            "Бот не налаштовано.\n\nВкажіть токен бота та chat_id у:\n"
            "Налаштування → Резервні копії → Telegram.",
        )
        return None
    return token, chat


def send_document_telegram(
    parent, file_path: str, caption: str, delete_after: bool = False
) -> bool:
    """Запустити фонову відправку файлу в Telegram та показати результат.

    Повертає False, якщо відправку не розпочато (бот не налаштовано).
    Результат (успіх/помилка) повідомляється окремим діалогом.
    delete_after=True — видалити тимчасовий файл після відправки.
    """
    prefs = telegram_prefs_or_warn(parent)
    if prefs is None:
        return False
    token, chat = prefs
    worker = FunctionWorker(send_telegram_document, token, chat, file_path, caption)

    def _done(ok: bool):
        if delete_after:
            _cleanup(file_path)
        _report(parent, ok)

    def _fail(message: str):
        if delete_after:
            _cleanup(file_path)
        _report_error(parent, message)

    worker.result.connect(_done)
    worker.error.connect(_fail)
    # Утримуємо worker у батька, щоб Python не зібрав його сміттям під час роботи
    parent._tg_doc_worker = worker
    worker.finished.connect(lambda: setattr(parent, "_tg_doc_worker", None))
    worker.start()
    return True


def _cleanup(path: str):
    with suppress(OSError):
        os.unlink(path)


def _report(parent, ok: bool):
    if ok:
        QMessageBox.information(parent, "Telegram", "✅ Файл надіслано в чат")
    else:
        QMessageBox.warning(
            parent,
            "Telegram",
            "Не вдалося надіслати файл.\nПеревірте токен, chat_id та інтернет-з'єднання.",
        )


def _report_error(parent, message: str):
    QMessageBox.critical(parent, "Telegram", f"Помилка відправки:\n{message}")
