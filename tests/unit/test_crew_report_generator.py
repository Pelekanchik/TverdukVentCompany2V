"""Тести генератора PDF-звіту бригади про виконання (чек-лист)."""

import os
from datetime import date

from tests.unit.test_crew_plan_generator import _works


def test_generate_crew_report_creates_pdf(tmp_path):
    from ventilation_company.crew_report_generator import generate_crew_report

    path = str(tmp_path / "zvit.pdf")
    generate_crew_report(
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


def test_generate_crew_report_without_company(tmp_path):
    from ventilation_company.crew_report_generator import generate_crew_report

    path = str(tmp_path / "zvit-min.pdf")
    generate_crew_report(
        [_works()[0]],
        "Бригада №1",
        date(2026, 10, 5),
        date(2026, 10, 11),
        path,
    )
    assert os.path.getsize(path) > 2000


def test_generate_crew_report_empty(tmp_path):
    from ventilation_company.crew_report_generator import generate_crew_report

    path = str(tmp_path / "zvit-empty.pdf")
    generate_crew_report([], "", date(2026, 10, 5), date(2026, 10, 11), path)
    assert os.path.getsize(path) > 1000
