"""Потреби виробництва в матеріалах vs залишки складу.

Для невиконаних завдань черги виробництва рахує потребу в матеріалах
(матеріал береться з виробу проєкту), шукає відповідну позицію на
складі (за збігом назви) і рахує: потрібно / на складі / зарезервовано /
доступно / чи вистачає. Доступне можна одним кліком зарезервувати
під виробництво (метод reserve_available).
"""

from __future__ import annotations

from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.production_task_repo import (
    ProductionTaskRepository,
)
from ventilation_company.database.repositories.warehouse_repo import WarehouseRepository

# Статуси забезпеченості матеріалу.
STATUS_OK = "ok"  # доступно >= потрібно
STATUS_PARTIAL = "partial"  # доступно > 0, але менше потрібно
STATUS_MISSING = "missing"  # позиції немає або доступно 0


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def match_warehouse_item(material: str, items: list[dict]) -> dict | None:
    """Знайти позицію складу за назвою матеріалу (точний збіг → підрядок)."""
    needle = _norm(material)
    if not needle:
        return None
    for item in items:  # точний збіг — найкращий
        if _norm(item.get("name") or "") == needle:
            return item
    for item in items:  # підрядок у будь-який бік
        name = _norm(item.get("name") or "")
        if needle in name or name in needle:
            return item
    return None


def _product_materials_by_project(project_ids: set[int]) -> dict[int, dict[str, str]]:
    """{project_id: {product_name: material}} для проєктів черги."""
    result: dict[int, dict[str, str]] = {}
    for pid in project_ids:
        try:
            products = ProductRepository.get_all(project_id=pid) or []
        except Exception:  # noqa: BLE001 — позицію просто не знайдемо
            products = []
        result[pid] = {(p.get("name") or ""): (p.get("material") or "") for p in products}
    return result


def required_materials(tasks: list[dict] | None = None) -> dict[str, float]:
    """Потреба в матеріалах по невиконаних завданнях: {матеріал: кількість}.

    Без матеріалу вироби групуються під ключ «—» (перевіряти не треба,
    але видно, що вони є).
    """
    if tasks is None:
        tasks = ProductionTaskRepository.get_all()
    active = [t for t in tasks if t.get("status") != "готово"]
    projects = {t["project_id"] for t in active}
    materials_map = _product_materials_by_project(projects)

    needed: dict[str, float] = {}
    for t in active:
        material = materials_map.get(t["project_id"], {}).get(t["product_name"], "")
        key = material.strip() or "—"
        needed[key] = needed.get(key, 0.0) + float(t.get("quantity") or 1)
    return needed


def check_materials(tasks: list[dict] | None = None) -> list[dict]:
    """Звірка потреб зі складом: рядок на кожен матеріал.

    Рядок: material, needed, item_id, item_name, unit, on_hand, reserved,
    available, status.
    """
    needed = required_materials(tasks)
    items = WarehouseRepository.list_items() or []
    rows = []
    for material, qty in sorted(needed.items(), key=lambda kv: -kv[1]):
        if material == "—":
            continue  # без матеріалу звіряти нічого
        item = match_warehouse_item(material, items)
        if item is None:
            rows.append(
                {
                    "material": material,
                    "needed": qty,
                    "item_id": None,
                    "item_name": "",
                    "unit": "",
                    "on_hand": 0.0,
                    "reserved": 0.0,
                    "available": 0.0,
                    "status": STATUS_MISSING,
                }
            )
            continue
        available = float(item.get("available", 0.0))
        if available >= qty:
            status = STATUS_OK
        elif available > 0:
            status = STATUS_PARTIAL
        else:
            status = STATUS_MISSING
        rows.append(
            {
                "material": material,
                "needed": qty,
                "item_id": item["id"],
                "item_name": item["name"],
                "unit": item.get("unit") or "",
                "on_hand": float(item.get("quantity", 0.0)),
                "reserved": float(item.get("reserved", 0.0)),
                "available": available,
                "status": status,
            }
        )
    return rows


def reserve_available(rows: list[dict]) -> tuple[int, list[str]]:
    """Зарезервувати доступне під потреби (мінімум із потрібного й доступного).

    Повертає (кількість позицій, де зроблено резерв, список помилок).
    """
    reserved_count = 0
    errors: list[str] = []
    for row in rows:
        item_id = row.get("item_id")
        if item_id is None:
            continue
        qty = min(float(row["needed"]), float(row["available"]))
        if qty <= 0:
            continue
        try:
            WarehouseRepository.reserve(item_id, qty)
            reserved_count += 1
        except Exception as e:  # noqa: BLE001 — збираємо всі помилки разом
            errors.append(f"{row['material']}: {e}")
    return reserved_count, errors
