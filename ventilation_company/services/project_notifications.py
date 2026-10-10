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


def _project_payment_context(payment: dict) -> dict | None:
    """Оплачено/залишок/% по проєкту оплати; None, якщо порахувати не вдалося."""
    pid = payment.get("project_id")
    if not pid:
        return None
    try:
        from ventilation_company.database.repositories.payment_repo import PaymentRepository
        from ventilation_company.database.repositories.product_repo import ProductRepository
        from ventilation_company.database.repositories.project_expense_repo import (
            ProjectExpenseRepository,
        )
        from ventilation_company.database.repositories.project_work_repo import (
            ProjectWorkRepository,
        )
        from ventilation_company.services.receivables import (
            _project_total_customer,
            payment_summary,
        )

        products = ProductRepository.get_all(project_id=pid)
        works = ProjectWorkRepository.get_all(pid)
        expenses = ProjectExpenseRepository.get_all(pid)
        total = _project_total_customer(products, works, expenses)
        if total <= 0:
            return None
        payments = PaymentRepository.list_by_project(pid)
        return payment_summary(payments, total)
    except Exception:  # noqa: BLE001 — сповіщення не повинне падати
        return None


def build_payment_received_text(payment: dict) -> str:
    """Текст звіту про вхідну оплату: сума, проєкт, замовник, призначення, залишок."""
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
    context = _project_payment_context(payment)
    if context is not None:
        lines.append("")
        lines.append(
            f"✅ Оплачено за проєктом: {_fmt_money(context['paid'])} ({context['percent']} %)"
        )
        if context["overpaid"]:
            lines.append(f"⚠️ Переплата: {_fmt_money(-context['balance'])}")
        else:
            lines.append(f"🧾 Залишок до сплати: {_fmt_money(context['balance'])}")
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


# Статуси, які не потребують нагадувань (проєкт завершено)
_DONE_STATUSES = {"Закрито", "Відвантажено"}


def build_status_changed_text(project: dict, old_status: str, new_status: str) -> str:
    """Текст сповіщення про зміну статусу проєкту."""
    name = project.get("name") or f"Проєкт #{project.get('id')}"
    number = project.get("project_number") or ""
    lines = ["🔄 Зміна статусу проєкту — VentCompany", ""]
    lines.append(f"🏗 Проєкт: {name}" + (f" ({number})" if number else ""))
    lines.append(f"📊 Статус: {old_status or '—'} → {new_status or '—'}")
    lines.append(f"🕒 {datetime.now():%d.%m.%Y %H:%M}")
    return "\n".join(lines)


def notify_project_status_changed(project: dict, old_status: str, new_status: str) -> bool:
    """Надіслати сповіщення про зміну статусу проєкту (не критичне, без винятків)."""
    if not new_status or old_status == new_status:
        return False
    _enabled, token, chat = cloud_backup_preferences()
    if not token or not chat:
        return False
    return send_telegram_message(
        token, chat, build_status_changed_text(project, old_status, new_status)
    )


def _stuck_threshold_days() -> int:
    """Скільки днів без оновлення вважати проєкт «завислим» (налаштування, дефолт 14)."""
    try:
        from ventilation_company.database.repositories.app_settings_repository import (
            AppSettingsRepository,
        )

        raw = AppSettingsRepository().get("app.stuck_projects_days", "14").strip()
        days = int(raw)
        return days if days > 0 else 14
    except Exception:  # noqa: BLE001
        return 14


def build_stuck_projects_text(projects: list[dict]) -> str:
    """Дайджест проєктів, що довго не оновлювалися."""
    lines = ["⏰ Нагадування — VentCompany", ""]
    lines.append(f"Проєкти без руху понад {projects[0].get('_threshold_days', 14)} днів:")
    for p in projects:
        name = p.get("name") or f"Проєкт #{p.get('id')}"
        number = p.get("project_number") or ""
        updated = str(p.get("updated_at") or "")[:10]
        lines.append(
            f"• {name}"
            + (f" ({number})" if number else "")
            + f" — {p.get('status') or '—'}, останнє оновлення {updated}"
        )
    lines.append("")
    lines.append(f"🕒 {datetime.now():%d.%m.%Y %H:%M}")
    return "\n".join(lines)


def check_stuck_projects(now=None) -> bool:
    """Знайти «завислі» проєкти й надіслати дайджест у Telegram.

    Проєкт «завислий»: статус не Закрито/Відвантажено і updated_at старіший
    за поріг (app.stuck_projects_days, дефолт 14). Повертає True, якщо
    повідомлення надіслано. Без бота чи без завислих проєктів — False.
    """
    _enabled, token, chat = cloud_backup_preferences()
    if not token or not chat:
        return False
    try:
        from ventilation_company.database.repositories.project_repo import ProjectRepository

        days = _stuck_threshold_days()
        now = now or datetime.now()
        stuck = []
        for p in ProjectRepository.list_all():
            if (p.get("status") or "") in _DONE_STATUSES:
                continue
            updated = p.get("updated_at")
            if updated is None:
                continue
            if isinstance(updated, str):
                with contextlib.suppress(ValueError):
                    updated = datetime.fromisoformat(updated)
            if not isinstance(updated, datetime):
                continue
            if (now - updated).days >= days:
                row = dict(p)
                row["_threshold_days"] = days
                stuck.append(row)
        if not stuck:
            return False
        return send_telegram_message(token, chat, build_stuck_projects_text(stuck))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram: перевірка завислих проєктів не вдалася: %s", exc)
        return False
