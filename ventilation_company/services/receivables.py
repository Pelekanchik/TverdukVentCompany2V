"""Дебіторка: підсумки по оплатах по всіх проєктах (сервісний шар).

Використовується вкладкою «Гроші» (gui_pyside6/money_tab.py) та карткою
проєкту (payment_summary).
"""

from __future__ import annotations

from ventilation_company.database.repositories.payment_repo import PaymentRepository
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_expense_repo import (
    ProjectExpenseRepository,
)
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository


def payment_summary(payments: list[dict], total_customer: float) -> dict:
    """Підсумок по оплатах проєкту.

    «Сплачено» — надходження (вхідні) мінус повернення (вихідні).
    Повертає paid, balance, percent (0..100) та overpaid.
    """
    paid = 0.0
    for p in payments:
        amount = float(p.get("amount") or 0)
        if (p.get("type") or "вхідний") == "вхідний":
            paid += amount
        else:
            paid -= amount
    balance = total_customer - paid
    percent = min(100.0, round(paid / total_customer * 100, 1)) if total_customer > 0 else 0.0
    return {
        "paid": round(paid, 2),
        "balance": round(balance, 2),
        "percent": percent,
        "overpaid": total_customer > 0 and paid > total_customer,
    }


def _project_total_customer(products: list[dict], works: list[dict], expenses: list[dict]) -> float:
    """Вартість проєкту для замовника: виробі (зі знижкою) + роботи + дод. витрати."""
    base = sum(
        (
            float(item.get("discounted_price") or 0)
            if float(item.get("discounted_price") or 0) > 0
            else float(item.get("total_price") or 0)
        )
        for item in products
    )
    works_total = sum(float(item.get("total_price") or 0) for item in works)
    plus_expenses = sum(
        float(item.get("total_price") or 0)
        for item in expenses
        if (item.get("direction") or "minus") == "plus"
    )
    return round(base + works_total + plus_expenses, 2)


def build_receivables(projects: list[dict] | None = None) -> list[dict]:
    """Зведення по оплатах по проєктах (дебіторка).

    Для кожного проєкту: вартість для замовника, сплачено, залишок, %,
    кількість оплат та дата останньої. Сортування: спершу найбільший борг.
    """
    if projects is None:
        projects = ProjectRepository.list_all()
    rows = []
    for p in projects:
        pid = int(p.get("id") or 0)
        if not pid:
            continue
        products = ProductRepository.get_all(project_id=pid)
        works = ProjectWorkRepository.get_all(pid)
        expenses = ProjectExpenseRepository.get_all(pid)
        payments = PaymentRepository.list_by_project(pid)

        total = _project_total_customer(products, works, expenses)
        s = payment_summary(payments, total)
        last_payment = max((str(pm.get("date") or "") for pm in payments), default="")

        rows.append(
            {
                "project_id": pid,
                "project_number": p.get("project_number") or "",
                "name": p.get("name") or "",
                "client": p.get("client") or "",
                "status": p.get("status") or "",
                "total": total,
                "paid": s["paid"],
                "balance": s["balance"],
                "percent": s["percent"],
                "overpaid": s["overpaid"],
                "payments_count": len(payments),
                "last_payment": last_payment[:10],
            }
        )
    rows.sort(key=lambda r: (r["overpaid"], -max(r["balance"], 0.0)))
    return rows


def receivables_totals(rows: list[dict]) -> dict:
    """Загальні підсумки дебіторки."""
    return {
        "projects": len(rows),
        "total": round(sum(r["total"] for r in rows), 2),
        "paid": round(sum(r["paid"] for r in rows), 2),
        "debt": round(sum(max(r["balance"], 0.0) for r in rows), 2),
        "overpaid": round(sum(max(-r["balance"], 0.0) for r in rows), 2),
    }


_DONE_STATUSES = {"завершено", "completed", "done", "закрито", "виконано"}


def is_overdue(project_status: str | None, balance: float) -> bool:
    """Прострочена заборгованість: проєкт завершено, а борг залишився."""
    return (project_status or "").strip().lower() in _DONE_STATUSES and balance > 0
