"""Тести генератора акта виконаних робіт (PDF)."""

import os


def test_generate_act_creates_pdf(tmp_path):
    from ventilation_company.act_generator import generate_act

    items = [
        {
            "name": "Монтаж повітропроводів",
            "description": "",
            "quantity": 12,
            "unit": "м2",
            "price": 280.0,
        },
        {
            "name": "Повітропровід Ø400",
            "description": "Виріб",
            "quantity": 2,
            "unit": "шт",
            "price": 3500.0,
        },
    ]
    path = str(tmp_path / "Акт.pdf")
    generate_act(
        {
            "name": "Тестовий проєкт",
            "project_number": "PRJ-1",
            "client": "ТОВ «Клієнт»",
            "contract_number": "ДГ-2026-001",
            "company": {
                "name": "ПП «ВентБуд»",
                "address": "м. Львів, вул. Монтажна, 3",
                "phone": "+38 (032) 555-44-33",
                "edrpou": "98765432",
                "signatory": "Директор Твердух В.М.",
                "city": "м. Львів",
            },
        },
        items,
        path,
    )
    assert os.path.exists(path)
    assert os.path.getsize(path) > 2000
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_generate_act_without_company(tmp_path):
    """Акт без реквізитів фірми (стара поведінка) теж працює."""
    from ventilation_company.act_generator import generate_act

    path = str(tmp_path / "Акт-дефолт.pdf")
    generate_act(
        {"name": "Проєкт", "client": "ФОП Клієнт"},
        [{"name": "Доставка", "quantity": 1, "unit": "рейс", "price": 1200.0}],
        path,
    )
    assert os.path.getsize(path) > 2000


from ventilation_company.act_generator import amount_in_words  # noqa: E402


class TestAmountInWords:
    def test_zero(self):
        assert amount_in_words(0) == "нуль гривень 00 копійок"

    def test_single_hryvnia(self):
        assert amount_in_words(1) == "одна гривня 00 копійок"

    def test_hryvnias_plural(self):
        assert amount_in_words(3) == "три гривні 00 копійок"

    def test_genitive_many(self):
        assert amount_in_words(11) == "одинадцять гривень 00 копійок"

    def test_thousands(self):
        result = amount_in_words(2100)
        assert result.startswith("дві тисячі сто")
        assert result.endswith("гривень 00 копійок")

    def test_one_thousand(self):
        assert amount_in_words(1000).startswith("одна тисяча")

    def test_millions_masculine(self):
        result = amount_in_words(2000000)
        assert result.startswith("два мільйони")

    def test_kopecks(self):
        result = amount_in_words(1234.5)
        assert result.endswith("50 копійок")
        assert "одна тисяча двісті тридцять чотири" in result

    def test_rounding(self):
        assert amount_in_words(0.99) == "нуль гривень 99 копійок"


def test_act_data_defaults():
    from ventilation_company.act_generator import ActData

    data = ActData()
    assert data.vat_percent == 20.0
    assert data.items == []
    assert data.city == "м. Київ"
