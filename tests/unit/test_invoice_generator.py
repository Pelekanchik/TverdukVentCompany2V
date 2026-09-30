"""Тести генератора рахунка на оплату (PDF)."""

import os


def test_generate_invoice_creates_pdf(tmp_path):
    from ventilation_company.invoice_generator import generate_invoice

    items = [
        {
            "name": "Повітропровід Ø400",
            "description": "Виріб",
            "quantity": 2,
            "unit": "шт",
            "price": 3500.0,
        },
        {
            "name": "Монтаж обладнання",
            "description": "Монтажні роботи",
            "quantity": 4,
            "unit": "шт",
            "price": 2000.0,
        },
    ]
    path = str(tmp_path / "Рахунок.pdf")
    generate_invoice(
        {
            "name": "Тестовий проєкт",
            "project_number": "PRJ-1",
            "client": "ТОВ «Клієнт»",
            "address": "м. Харків, вул. Заводська, 10",
            "contract_number": "ДГ-2026-001",
            "company": {
                "name": "ПП «ВентБуд»",
                "address": "м. Львів, вул. Монтажна, 3",
                "phone": "+38 (032) 555-44-33",
                "email": "office@ventbud.ua",
                "edrpou": "98765432",
                "signatory": "Директор Твердух В.М.",
                "bank_name": "АТ «ПриватБанк»",
                "iban": "UA11 1111 1111 1111 1111 1111 11",
                "mfo": "305299",
            },
        },
        items,
        path,
    )
    assert os.path.exists(path)
    assert os.path.getsize(path) > 2000
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_generate_invoice_without_bank_details(tmp_path):
    """Рахунок без банківських реквізитів (старі дані) — дефолти, без помилок."""
    from ventilation_company.invoice_generator import generate_invoice

    path = str(tmp_path / "Рахунок-дефолт.pdf")
    generate_invoice(
        {"name": "Проєкт", "client": "ФОП Клієнт"},
        [{"name": "Доставка", "quantity": 1, "unit": "рейс", "price": 1200.0}],
        path,
    )
    assert os.path.getsize(path) > 2000


def test_invoice_data_defaults():
    from ventilation_company.invoice_generator import InvoiceData

    data = InvoiceData()
    assert data.vat_percent == 20.0
    assert data.items == []
    assert data.iban.startswith("UA")
    assert data.mfo
