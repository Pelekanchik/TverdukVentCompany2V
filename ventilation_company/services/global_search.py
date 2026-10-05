"""Глобальний пошук по програмі (v2.9): проєкти, вироби, роботи, креслення, клієнти.

Сервісний шар для діалогу пошуку (Ctrl+G). Кожен результат — dict:
    kind      — projects | products | works | drawings | clients
    project_id — до якого проєкту прив'язано (для клієнтів — None)
    title     — головний текст
    subtitle  — додатковий контекст
"""

from __future__ import annotations

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_drawing_repo import (
    ProjectDrawingRepository,
)
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository

_LIMIT_PER_KIND = 20


def _match(needle: str, *fields) -> bool:
    return any(needle in str(f or "").lower() for f in fields)


def search_all(query: str, limit_per_kind: int = _LIMIT_PER_KIND) -> list[dict]:
    """Пошук за фрагментом по всіх розділах. Порожній запит → порожній результат."""
    needle = (query or "").strip().lower()
    if not needle:
        return []
    results: list[dict] = []

    # Проєкти
    for p in ProjectRepository.list_all():
        if not _match(needle, p.get("name"), p.get("project_number"), p.get("client")):
            continue
        results.append(
            {
                "kind": "projects",
                "project_id": p.get("id"),
                "title": f"{p.get('project_number') or ''} {p.get('name') or ''}".strip(),
                "subtitle": f"Проєкт · {p.get('client') or '—'} · {p.get('status') or ''}",
            }
        )
        if sum(1 for r in results if r["kind"] == "projects") >= limit_per_kind:
            break

    # Вироби
    for item in ProductRepository.search(query=query.strip()):
        results.append(
            {
                "kind": "products",
                "project_id": item.get("project_id"),
                "title": item.get("name") or "—",
                "subtitle": f"Виріб · {item.get('product_type') or ''}",
            }
        )
        if sum(1 for r in results if r["kind"] == "products") >= limit_per_kind:
            break

    # Роботи (по всіх проєктах)
    projects = ProjectRepository.list_all()
    works_count = 0
    for p in projects:
        if works_count >= limit_per_kind:
            break
        pid = int(p.get("id") or 0)
        if not pid:
            continue
        for w in ProjectWorkRepository.get_all(pid):
            if works_count >= limit_per_kind:
                break
            if not _match(needle, w.get("work_name"), w.get("crew")):
                continue
            results.append(
                {
                    "kind": "works",
                    "project_id": pid,
                    "title": w.get("work_name") or "—",
                    "subtitle": f"Робота · {p.get('name') or ''}"
                    + (f" · {w.get('work_date')}" if w.get("work_date") else ""),
                }
            )
            works_count += 1

    # Креслення (по всіх проєктах)
    drawings_count = 0
    for p in projects:
        if drawings_count >= limit_per_kind:
            break
        pid = int(p.get("id") or 0)
        if not pid:
            continue
        for d in ProjectDrawingRepository.get_by_project(pid):
            if drawings_count >= limit_per_kind:
                break
            if not _match(needle, d.get("filename"), d.get("drawing_type")):
                continue
            results.append(
                {
                    "kind": "drawings",
                    "project_id": pid,
                    "title": d.get("filename") or "—",
                    "subtitle": f"Креслення · {p.get('name') or ''}",
                }
            )
            drawings_count += 1

    # Клієнти
    for c in ClientRepository.list_all():
        if not _match(
            needle, c.get("name"), c.get("phone"), c.get("contact_person"), c.get("edrpou")
        ):
            continue
        results.append(
            {
                "kind": "clients",
                "project_id": None,
                "title": c.get("name") or "—",
                "subtitle": f"Клієнт · {c.get('phone') or ''}".strip(),
            }
        )
        if sum(1 for r in results if r["kind"] == "clients") >= limit_per_kind:
            break

    return results
