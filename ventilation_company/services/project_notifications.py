"""Telegram-сповіщення про події з проєктами.

Використовує того самого бота та chat_id, що й хмарний бекап
(Налаштування → Резервні копії → Telegram). Ніколи не підіймає винятки —
у разі помилки лише логує, щоб сповіщення не ламало основний сценарій.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.utils.cloud_backup import (
    cloud_backup_preferences,
    send_telegram_message,
)
from ventilation_company.utils.logging_config import get_logger

logger = get_logger("project_notifications")


def _fmt_money(value) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    return f"{amount:,.2f} ₴".replace(",", " ")


def _client_label(raw: str) -> str:
    """«Назва (телефон)» → «Назва» (combo зберігає display-рядок)."""
    raw = (raw or "").strip()
    if raw.endswith(")") and "(" in raw:
        return raw.rsplit("(", 1)[0].strip()
    return raw


def build_project_created_text(project: dict) -> str:
    """Текст звіту про новий проєкт: дані замовника + дані цього проєкту."""
    client: dict = {}
    client_id = project.get("client_id")
    if client_id:
        with contextlib.suppress(Exception):
            client = ClientRepository.get(client_id) or {}

    price = project.get("discounted_price") or project.get("customer_price") or 0

    lines = ["🆕 Новий проєкт у VentCompany", ""]
    lines.append("🏗 Проєкт:")
    lines.append(f"• Назва: {project.get('name') or '—'}")
    lines.append(f"• Номер: {project.get('project_number') or '—'}")
    lines.append(f"• Статус: {project.get('status') or 'Новий'}")
    lines.append(f"• Ціна замовнику: {_fmt_money(price)}")
    if project.get("discounted_price"):
        lines.append(f"• Зі знижкою: {_fmt_money(project.get('discounted_price'))}")
    lines.append(f"• Собівартість: {_fmt_money(project.get('cost_price'))}")
    lines.append(f"• Прибуток: {_fmt_money(project.get('profit'))}")

    lines.append("")
    lines.append("👤 Замовник:")
    client_name = client.get("name") or _client_label(str(project.get("client") or ""))
    lines.append(f"• Назва: {client_name or '—'}")
    if client:
        lines.append(f"• Контактна особа: {client.get('contact_person') or '—'}")
        lines.append(f"• Телефон: {client.get('phone') or '—'}")
        lines.append(f"• Email: {client.get('email') or '—'}")
        lines.append(f"• Адреса: {client.get('address') or '—'}")

    lines.append("")
    lines.append(f"🕒 Створено: {datetime.now():%d.%m.%Y %H:%M}")
    return "\n".join(lines)


def notify_project_created(project: dict) -> bool:
    """Надіслати звіт про новий проєкт у Telegram-чат.

    Повертає True, якщо повідомлення надіслано; False — бот не налаштовано
    або відправка не вдалася. Винятки не підіймає.
    """
    _enabled, token, chat = cloud_backup_preferences()
    if not token or not chat:
        logger.info("Telegram: звіт про проєкт пропущено — бот не налаштовано")
        return False
    ok = send_telegram_message(token, chat, build_project_created_text(project))
    if ok:
        logger.info("Telegram: звіт про проєкт %s надіслано", project.get("project_number"))
    else:
        logger.warning(
            "Telegram: не вдалося надіслати звіт про проєкт %s", project.get("project_number")
        )
    return ok


def build_payment_received_text(payment: dict) -> str:
    """Текст звіту про вхідну оплату: сума, проєкт, замовник, призначення."""
    client: dict = {}
    client_id = payment.get("client_id")
    if client_id:
        with contextlib.suppress(Exception):
            client = ClientRepository.get(client_id) or {}

    lines = ["💵 Надходження оплати — VentCompany", ""]
    lines.append(f"💰 Сума: {_fmt_money(payment.get('amount'))}")
    lines.append(f"🏗 Проєкт: {payment.get('project_name') or '—'}")
    lines.append(f"👤 Замовник: {client.get('name') or '—'}")
    if payment.get("purpose"):
        lines.append(f"📝 Призначення: {payment['purpose']}")
    if payment.get("date"):
        lines.append(f"📅 Дата: {payment['date']}")
    return "\n".join(lines)


def notify_payment_created(payment: dict) -> bool:
    """Надіслати звіт про вхідну оплату у Telegram (вихідні платежі ігнорує).

    Ніколи не підіймає винятки й не ламає основний сценарій додавання оплати.
    """
    if (payment.get("type") or "вхідний") != "вхідний":
        return False
    _enabled, token, chat = cloud_backup_preferences()
    if not token or not chat:
        logger.info("Telegram: звіт про оплату пропущено — бот не налаштовано")
        return False
    ok = send_telegram_message(token, chat, build_payment_received_text(payment))
    if ok:
        logger.info("Telegram: звіт про оплату %s надіслано", payment.get("id"))
    else:
        logger.warning("Telegram: не вдалося надіслати звіт про оплату %s", payment.get("id"))
    return ok
