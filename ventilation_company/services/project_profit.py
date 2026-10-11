"""Фінансовий зріз проєкту: дохід, витрати, прибуток, маржа (v2.9).

Чисті функції — використовуються карткою проєкту та тестами.
"""

from __future__ import annotations


def compute_financials(
    products: list[dict],
    works: list[dict],
    expenses: list[dict],
    payments: list[dict],
    discounted_price: float = 0,
) -> dict:
    """Розрахувати фінансові показники проєкту.

    Дохід = вироби (зі знижкою, якщо задана) + роботи + витрати-надходження.
    Витрати = собівартість виробів + витрати-списання.
    Повертає dict з ключами: income, cost, profit, margin_pct, paid, balance.
    """
    base = sum(
        (
            float(item.get("discounted_price") or 0)
            if float(item.get("discounted_price") or 0) > 0
            else float(item.get("total_price") or 0)
        )
        for item in products
    )
    # Якщо на рівні проєкту задана знижена ціна — вона замінює суму виробів
    if discounted_price and discounted_price > 0:
        base = float(discounted_price)

    works_total = sum(float(item.get("total_price") or 0) for item in works)
    plus_expenses = sum(
        float(item.get("total_price") or 0)
        for item in expenses
        if (item.get("direction") or "minus") == "plus"
    )
    minus_expenses = sum(
        float(item.get("total_price") or 0)
        for item in expenses
        if (item.get("direction") or "minus") != "plus"
    )
    cost = sum(
        float(item.get("cost_price") or 0) * float(item.get("quantity") or 1) for item in products
    )

    income = round(base + works_total + plus_expenses, 2)
    total_cost = round(cost + minus_expenses, 2)
    profit = round(income - total_cost, 2)
    margin_pct = round(profit / income * 100, 1) if income > 0 else 0.0

    paid = 0.0
    for p in payments:
        amount = float(p.get("amount") or 0)
        if (p.get("type") or "вхідний") == "вхідний":
            paid += amount
        else:
            paid -= amount

    return {
        "income": income,
        "cost": total_cost,
        "profit": profit,
        "margin_pct": margin_pct,
        "paid": round(paid, 2),
        "balance": round(income - paid, 2),
    }
