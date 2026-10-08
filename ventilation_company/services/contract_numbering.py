"""Автонумерація документів проєкту: ДГ/Р/АК-YYYYMMDD-NNN.

Номер формується за поточну дату з послідовністю по дню. Зберігається
у проєкті (projects.<key>): повторне формування документа повертає той
самий номер, а новий проєкт отримує наступний вільний.

Префікси: ДГ — договір, Р — рахунок, АК — акт виконаних робіт.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date, datetime

from ventilation_company.database.repositories.project_repo import ProjectRepository

logger = logging.getLogger(__name__)

# Типи документів із префіксами номерів і колонкою у projects
DOCUMENT_NUMBER_KEYS: dict[str, str] = {
    "contract_number": "ДГ",
    "invoice_number": "Р",
    "act_number": "АК",
}


def compute_next_number(
    existing: Iterable[str], today: date | None = None, prefix: str = "ДГ"
) -> str:
    """Наступний вільний номер за списком уже виданих.

    Враховує лише номери поточного дня у форматі <префікс>-YYYYMMDD-NNN;
    сміття та чужі формати ігноруються.
    """
    day = (today or datetime.now()).strftime("%Y%m%d")
    head = f"{prefix}-{day}"
    seqs: list[int] = []
    for num in existing:
        if not num or not num.startswith(head + "-"):
            continue
        tail = num.rsplit("-", 1)[-1]
        if tail.isdigit():
            seqs.append(int(tail))
    return f"{head}-{max(seqs, default=0) + 1:03d}"


def _taken_numbers(key: str = "contract_number") -> list[str]:
    """Усі видані номери документа з БД (незчитувані — як порожні)."""
    try:
        projects = ProjectRepository.list_all()
    except Exception:  # noqa: BLE001 — без БД нумеруємо від -001
        logger.exception("Не вдалося прочитати номери %s із БД", key)
        return []
    return [str(p.get(key) or "") for p in projects]


def next_document_number(key: str = "contract_number") -> str:
    return compute_next_number(_taken_numbers(key), prefix=DOCUMENT_NUMBER_KEYS[key])


def ensure_document_number(
    project_id: int, project_data: dict, key: str, prefix: str | None = None
) -> str:
    """Номер документа для проєкту: існуючий або новий зі збереженням у БД.

    project_data оновлюється на місці, щоб UI одразу бачив номер.
    Помилка запису в БД не блокує формування документа — номер просто
    не закріпиться за проєктом.
    """
    existing = str(project_data.get(key) or "").strip()
    if existing:
        return existing
    number = compute_next_number(_taken_numbers(key), prefix=prefix or DOCUMENT_NUMBER_KEYS[key])
    try:
        ProjectRepository.update(project_id, {key: number})
        project_data[key] = number
    except Exception:  # noqa: BLE001 — документ важливіший за запис номера
        logger.exception("Не вдалося зберегти номер %s у проєкт #%s", number, project_id)
    return number


# ── Сумісні обгортки (договір — перший тип, що отримав нумерацію) ──


def next_contract_number() -> str:
    return next_document_number("contract_number")


def ensure_contract_number(project_id: int, project_data: dict) -> str:
    return ensure_document_number(project_id, project_data, "contract_number")
