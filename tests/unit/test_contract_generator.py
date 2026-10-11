"""Тести генератора договору (PDF)."""

import os


def test_generate_contract_creates_pdf(tmp_path):
    from ventilation_company.contract_generator import generate_contract

    path = str(tmp_path / "Договір.pdf")
    generate_contract(
        {
            "name": "Тестовий проєкт",
            "project_number": "PRJ-1",
            "client": "ТОВ «Клієнт»",
            "total_amount": 61073.99,
        },
        path,
    )
    assert os.path.exists(path)
    assert os.path.getsize(path) > 2000
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_contract_data_defaults():
    from ventilation_company.contract_generator import ContractData

    data = ContractData()
    assert data.vat_percent == 20.0
    assert data.delivery_days == 14
    assert data.warranty_months == 24
    assert "аванс" in data.payment_terms


def test_generate_contract_with_company_details(tmp_path):
    """Реквізити фірми з «Налаштування → Бізнес» не ламають генерацію."""
    from ventilation_company.contract_generator import generate_contract

    path = str(tmp_path / "Договір-реквізити.pdf")
    generate_contract(
        {
            "name": "Проєкт із реквізитами",
            "client": "ТОВ «Клієнт»",
            "total_amount": 50000,
            "company": {
                "name": "ПП «ВентБуд»",
                "address": "м. Львів, вул. Монтажна, 3",
                "phone": "+38 (032) 555-44-33",
                "email": "office@ventbud.ua",
                "website": "www.ventbud.ua",
                "edrpou": "98765432",
                "signatory": "Директор Твердух В.М.",
                "city": "м. Львів",
            },
        },
        path,
    )
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_generate_contract_with_partial_company(tmp_path):
    """Часткові реквізити (без частини полів) теж працюють."""
    from ventilation_company.contract_generator import generate_contract

    path = str(tmp_path / "Договір-часткові.pdf")
    generate_contract(
        {
            "name": "Проєкт",
            "client": "ФОП Клієнт",
            "company": {"name": "ФОП Твердух", "city": "м. Тернопіль"},
        },
        path,
    )
    assert os.path.getsize(path) > 2000
