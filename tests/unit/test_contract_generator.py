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
