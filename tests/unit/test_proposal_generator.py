"""Тести генератора комерційної пропозиції (PDF)."""

import os


def test_generate_proposal_creates_pdf(tmp_path):
    from ventilation_company.proposal_generator import generate_proposal

    items = [
        {
            "name": "Повітропровід Ø400",
            "description": "Повітропровід круглий",
            "quantity": 2,
            "unit": "шт",
            "price": 1500.0,
        },
        {
            "name": "Монтаж",
            "description": "Монтажні роботи",
            "quantity": 1,
            "unit": "шт",
            "price": 3000.0,
        },
    ]
    path = str(tmp_path / "КП.pdf")
    generate_proposal({"name": "Тестовий проєкт", "client": "ТОВ «Клієнт»"}, items, path)

    assert os.path.exists(path)
    size = os.path.getsize(path)
    assert size > 1000
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_generate_proposal_totals_and_terms(tmp_path):
    """Підсумки: 2×1500 + 1×3000 = 6000; ПДВ 20% = 1200; разом 7200."""
    from ventilation_company.proposal_generator import ProposalData, ProposalItem

    subtotal = 2 * 1500.0 + 1 * 3000.0
    data = ProposalData(
        project_name="Тест",
        items=[
            ProposalItem(name="A", quantity=2, price_per_unit=1500.0, total=3000.0),
            ProposalItem(name="B", quantity=1, price_per_unit=3000.0, total=3000.0),
        ],
        subtotal=subtotal,
        vat_amount=round(subtotal * 0.20, 2),
        total=round(subtotal * 1.20, 2),
    )
    assert data.total == 7200.0
    assert data.delivery_days == 14
    assert data.warranty_months == 24
    assert "аванс" in data.payment_terms


def test_generate_proposal_with_company_details(tmp_path):
    """Реквізити фірми з «Налаштування → Бізнес» не ламають генерацію КП."""
    from ventilation_company.proposal_generator import generate_proposal

    items = [{"name": "Монтаж", "quantity": 1, "unit": "шт", "price": 3000.0}]
    path = str(tmp_path / "КП-реквізити.pdf")
    generate_proposal(
        {
            "name": "Тестовий проєкт",
            "client": "ТОВ «Клієнт»",
            "company": {
                "name": "ПП «ВентБуд»",
                "address": "м. Львів, вул. Монтажна, 3",
                "phone": "+38 (032) 555-44-33",
                "email": "office@ventbud.ua",
                "website": "www.ventbud.ua",
                "edrpou": "98765432",
            },
        },
        items,
        path,
    )
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"
