"""Сервіс планування монтажних робіт (v2.9).

Зведений список робіт із датами по всіх проєктах — для вкладки
«Монтажі» (фільтр за бригадою та періодом).
"""

from __future__ import annotations

from datetime import date, timedelta

from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository


def in_period(work_date: str, date_from: date | None, date_to: date | None) -> bool:
    """Чи потрапляє дата роботи (ISO-рядок або '') у заданий період."""
    if not work_date:
        return False
    try:
        d = date.fromisoformat(str(work_date)[:10])
    except ValueError:
        return False
    if date_from is not None and d < date_from:
        return False
    return not (date_to is not None and d > date_to)


def period_bounds(mode: str, today: date | None = None) -> tuple[date | None, date | None]:
    """Межі періоду за режимом: all/today/week/month."""
    today = today or date.today()
    if mode == "today":
        return today, today
    if mode == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if mode == "month":
        start = today.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return start, end
    return None, None


def list_scheduled_works(
    crew: str = "",
    period: str = "all",
    today: date | None = None,
    projects: list[dict] | None = None,
) -> list[dict]:
    """Роботи з датами по всіх проєктах, відсортовані за датою.

    Параметри:
        crew — фільтр за бригадою (підрядок, case-insensitive);
        period — all | today | week | month;
        projects — опційно вже завантажені проєкти (для тестів).
    """
    date_from, date_to = period_bounds(period, today)
    if projects is None:
        projects = ProjectRepository.list_all()
    needle = crew.strip().lower()

    rows: list[dict] = []
    for p in projects:
        pid = int(p.get("id") or 0)
        if not pid:
            continue
        for w in ProjectWorkRepository.get_all(pid):
            if not in_period(w.get("work_date") or "", date_from, date_to):
                continue
            if needle and needle not in (w.get("crew") or "").lower():
                continue
            rows.append(
                {
                    "work_id": w["id"],
                    "project_id": pid,
                    "project_number": p.get("project_number") or "",
                    "project_name": p.get("name") or "",
                    "address": p.get("address") or "",
                    "client": p.get("client") or "",
                    "work_name": w.get("work_name") or "—",
                    "work_date": w.get("work_date") or "",
                    "crew": w.get("crew") or "",
                    "total_price": float(w.get("total_price") or 0),
                }
            )
    rows.sort(key=lambda r: (r["work_date"] or "9999", r["project_name"]))
    return rows


def list_crews(projects: list[dict] | None = None) -> list[str]:
    """Унікальні бригади/виконавці з робіт, що мають дату."""
    if projects is None:
        projects = ProjectRepository.list_all()
    crews: set[str] = set()
    for p in projects:
        pid = int(p.get("id") or 0)
        if not pid:
            continue
        for w in ProjectWorkRepository.get_all(pid):
            crew = (w.get("crew") or "").strip()
            if crew:
                crews.add(crew)
    return sorted(crews, key=str.casefold)
