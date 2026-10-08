"""Автонумерація договорів: ДГ-YYYYMMDD-NNN.

Номер формується за поточну дату з послідовністю по дню. Зберігається
у проєкті (projects.contract_number): повторне формування договору
повертає той самий номер, а новий проєкт отримує наступний вільний.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date, datetime

from ventilation_company.database.repositories.project_repo import ProjectRepository

logger = logging.getLogger(__name__)


def compute_next_number(existing: Iterable[str], today: date | None = None) -> str:
    """Наступний вільний номер за списком уже виданих.

    Враховує лише номери поточного дня у форматі ДГ-YYYYMMDD-NNN;
    сміття та чужі формати ігноруються.
    """
    day = (today or datetime.now()).strftime("%Y%m%d")
    prefix = f"ДГ-{day}"
    seqs: list[int] = []
    for num in existing:
        if not num or not num.startswith(prefix + "-"):
            continue
        tail = num.rsplit("-", 1)[-1]
        if tail.isdigit():
            seqs.append(int(tail))
    return f"{prefix}-{max(seqs, default=0) + 1:03d}"


def _taken_numbers() -> list[str]:
    """Усі видані номери договорів з БД (незчитувані — як порожні)."""
    try:
        projects = ProjectRepository.list_all()
    except Exception:  # noqa: BLE001 — без БД нумеруємо від -001
        logger.exception("Не вдалося прочитати номери договорів із БД")
        return []
    return [str(p.get("contract_number") or "") for p in projects]


def next_contract_number() -> str:
    return compute_next_number(_taken_numbers())


def ensure_contract_number(project_id: int, project_data: dict) -> str:
    """Номер договору для проєкту: існуючий або новий зі збереженням у БД.

    project_data оновлюється на місці, щоб UI одразу бачив номер.
    Помилка запису в БД не блокує формування договору — номер просто
    не закріпиться за проєктом.
    """
    existing = str(project_data.get("contract_number") or "").strip()
    if existing:
        return existing
    number = next_contract_number()
    try:
        ProjectRepository.update(project_id, {"contract_number": number})
        project_data["contract_number"] = number
    except Exception:  # noqa: BLE001 — договір важливіший за запис номера
        logger.exception("Не вдалося зберегти номер договору %s у проєкт #%s", number, project_id)
    return number
