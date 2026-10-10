"""Сервіс планування виробництва (черга цеху).

Логіка поверх ProductionTaskRepository:
  • додавання в чергу всіх виробів проєкту (з захистом від дублікатів),
  • сортування черги (пріоритет → термін → дата створення),
  • підсумки для шапки вкладки: кількості за статусами + прострочені,
  • скільки днів лишилось до терміну (від'ємне — на скільки прострочено).
"""

from __future__ import annotations

from datetime import datetime

from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.production_task_repo import (
    PRIORITY_ORDER,
    ProductionTaskRepository,
)


def _priority_rank(priority: str) -> int:
    try:
        return PRIORITY_ORDER.index(priority)
    except ValueError:
        return len(PRIORITY_ORDER)


def add_project_to_queue(
    project_id: int,
    product_names: list[str] | None = None,
    priority: str = "звичайний",
    planned_start=None,
    planned_end=None,
    notes: str = "",
) -> tuple[int, int]:
    """Додати вироби проєкту в чергу виробництва.

    product_names — обмежити вибраними виробами (None — усі).
    Повертає (додано, пропущено): пропускаються вироби, що вже є
    в черзі зі статусом не «готово» (той самий проєкт + назва).

    Винятки не підіймає: якщо вироби проєкту прочитати не вдалося —
    повертає (0, 0).
    """
    try:
        products = ProductRepository.get_all(project_id=project_id)
    except Exception:  # noqa: BLE001 — черга не повинна ламати інтерфейс
        return 0, 0

    existing = ProductionTaskRepository.get_by_project(project_id)
    active_names = {
        t["product_name"]
        for t in existing
        if t["status"] != "готово" and t["product_name"] in (product_names or [])
    }
    if product_names is None:
        active_names = {t["product_name"] for t in existing if t["status"] != "готово"}

    added = skipped = 0
    for p in products:
        name = p.get("name") or ""
        if not name:
            continue
        if product_names is not None and name not in product_names:
            continue
        if name in active_names:
            skipped += 1
            continue
        ProductionTaskRepository.create(
            project_id=project_id,
            product_name=name,
            quantity=int(p.get("quantity") or 1),
            priority=priority,
            planned_start=planned_start,
            planned_end=planned_end,
            notes=notes,
        )
        added += 1
    return added, skipped


def sorted_queue(status: str | None = None) -> list[dict]:
    """Черга у робочому порядку: пріоритет → термін → дата створення.

    Завдання без терміну — після тих, що з терміном. «Готово» виносимо
    в кінець незалежно від пріоритету, щоб черга показувала те, що треба робити.
    """
    tasks = ProductionTaskRepository.get_all(status=status)

    def key(t: dict):
        done = 1 if t["status"] == "готово" else 0
        end = t.get("planned_end")
        end_key = end.timestamp() if isinstance(end, datetime) else float("inf")
        created = t.get("created_at")
        created_key = created.timestamp() if isinstance(created, datetime) else 0.0
        return (done, _priority_rank(t.get("priority") or ""), end_key, created_key)

    return sorted(tasks, key=key)


def days_left(task: dict, now: datetime | None = None) -> int | None:
    """Днів до терміну (0 — сьогодні; від'ємне — прострочено на N днів)."""
    end = task.get("planned_end")
    if not isinstance(end, datetime):
        return None
    now = now or datetime.now()
    return (end.date() - now.date()).days


def summary(tasks: list[dict], now: datetime | None = None) -> dict:
    """Підсумки для шапки: кількості за статусами + список прострочених."""
    now = now or datetime.now()
    counts: dict[str, int] = {"в черзі": 0, "в роботі": 0, "готово": 0}
    overdue: list[dict] = []
    for t in tasks:
        status = t.get("status") or "в черзі"
        counts[status] = counts.get(status, 0) + 1
        left = days_left(t, now)
        if status != "готово" and left is not None and left < 0:
            overdue.append(t)
    return {"counts": counts, "overdue": overdue}
