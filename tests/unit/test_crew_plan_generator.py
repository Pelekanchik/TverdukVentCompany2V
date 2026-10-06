"""Тести генератора PDF-плану монтажів для бригад."""

import os
from datetime import date


def _works():
    return [
        {
            "work_id": 1,
            "project_id": 1,
            "project_number": "PRJ-1",
            "project_name": "Кафе «Смак»",
            "address": "вул. Шевченка, 10",
            "client": "ТОВ «Кафе»",
            "work_name": "Монтаж повітропроводів",
            "work_date": "2026-10-06",
            "crew": "Бригада №1",
            "total_price": 4500.0,
        },
        {
            "work_id": 2,
            "project_id": 1,
            "project_number": "PRJ-1",
            "project_name": "Кафе «Смак»",
            "address": "вул. Шевченка, 10",
            "client": "ТОВ «Кафе»",
            "work_name": "Монтаж вентилятора",
            "work_date": "2026-10-08",
            "crew": "Бригада №1",
            "total_price": 0.0,
        },
        {
            "work_id": 3,
            "project_id": 2,
            "project_number": "PRJ-2",
            "project_name": "Склад",
            "address": "",
            "client": "",
            "work_name": "Доставка",
            "work_date": "2026-10-07",
            "crew": "Бригада №2",
            "total_price": 800.0,
        },
        {
            "work_id": 4,
            "project_id": 3,
            "project_number": "PRJ-3",
            "project_name": "Офіс",
            "address": "пр. Незалежності, 5",
            "client": "ФОП Іваненко",
            "work_name": "Виїзд на замір",
            "work_date": "2026-10-06",
            "crew": "",
            "total_price": 500.0,
        },
    ]


def test_generate_crew_plan_creates_pdf(tmp_path):
    from ventilation_company.crew_plan_generator import generate_crew_plan

    path = str(tmp_path / "plan.pdf")
    generate_crew_plan(
        _works(),
        "",
        date(2026, 10, 5),
        date(2026, 10, 11),
        path,
        {"name": "ПП «ВентБуд»"},
    )
    assert os.path.exists(path)
    assert os.path.getsize(path) > 2000
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_generate_crew_plan_without_company_and_address(tmp_path):
    """План без реквізитів фірми та без адрес теж будується."""
    from ventilation_company.crew_plan_generator import generate_crew_plan

    path = str(tmp_path / "plan-min.pdf")
    generate_crew_plan(
        [_works()[2]],
        "Бригада №2",
        date(2026, 10, 5),
        date(2026, 10, 11),
        path,
    )
    assert os.path.getsize(path) > 2000


def test_generate_crew_plan_empty(tmp_path):
    from ventilation_company.crew_plan_generator import generate_crew_plan

    path = str(tmp_path / "plan-empty.pdf")
    generate_crew_plan([], "", date(2026, 10, 5), date(2026, 10, 11), path)
    assert os.path.getsize(path) > 1000
