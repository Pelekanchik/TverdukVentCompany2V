"""Тести решти розділу 5.2: бухгалтерський експорт, ціни постачальників, ролі."""

from datetime import date, datetime, timedelta

import pytest

# ── 5.2-3: експорт для бухгалтерії ──


def _payment(pid, days_ago, amount, ptype="вхідний", client_id=None):
    return {
        "id": pid,
        "client_id": client_id,
        "project_id": None,
        "date": datetime.now() - timedelta(days=days_ago),
        "amount": amount,
        "currency": "UAH",
        "type": ptype,
        "purpose": "Оплата за договором",
        "project_name": "Проєкт X",
        "notes": "",
    }


def test_payments_between_filters_period_and_adds_client(monkeypatch):
    from ventilation_company.database.repositories import client_repo, payment_repo
    from ventilation_company.services import accounting_export_service as svc

    monkeypatch.setattr(
        payment_repo.PaymentRepository,
        "list_all",
        staticmethod(
            lambda: [
                _payment(1, 5, 1000.0, client_id=3),  # в періоді
                _payment(2, 40, 2000.0, client_id=3),  # поза періодом
                _payment(3, 3, 500.0, ptype="вихідний"),  # витрата
            ]
        ),
    )
    monkeypatch.setattr(
        client_repo.ClientRepository,
        "get",
        staticmethod(lambda cid: {"name": "ТОВ «Клієнт»"}),
    )
    today = date.today()
    rows = svc.payments_between(today - timedelta(days=10), today)
    assert len(rows) == 2
    assert rows[0]["counterparty"] == "ТОВ «Клієнт»"
    assert rows[1]["type"] == "вихідний"


def test_export_csv_and_1c(tmp_path):
    from ventilation_company.services import accounting_export_service as svc

    payments = [
        {
            "date": date(2026, 10, 1),
            "counterparty": "ТОВ Клієнт",
            "type": "вхідний",
            "amount": 1200.0,
            "currency": "UAH",
            "purpose": "Аванс",
            "project": "П1",
            "notes": "",
        },
        {
            "date": date(2026, 10, 2),
            "counterparty": "Постачальник",
            "type": "вихідний",
            "amount": 300.0,
            "currency": "UAH",
            "purpose": "Метал",
            "project": "",
            "notes": "",
        },
    ]
    csv_path = tmp_path / "виписка.csv"
    svc.export_payments_csv(payments, str(csv_path))
    content = csv_path.read_text(encoding="utf-8-sig")
    assert "Дата" in content and "ТОВ Клієнт" in content
    assert "1200,00" in content  # десяткова кома для Excel

    onec_path = tmp_path / "виписка.txt"
    svc.export_payments_1c(payments, str(onec_path))
    onec = onec_path.read_text(encoding="cp1251")
    assert onec.startswith("1CClientBankExchange")
    assert "ВерсияФормата=1.02" in onec
    assert "ВсегоПоступило=1200.00" in onec
    assert "ВсегоСписано=300.00" in onec
    assert onec.rstrip().endswith("КонецФайла")
    assert onec.count("СекцияПлатежноеПоручение") == 2


def test_vat_report_math():
    from ventilation_company.services import accounting_export_service as svc

    today = date.today()
    payments = [
        {"date": today, "counterparty": "A", "type": "вхідний", "amount": 1200.0},
        {"date": today, "counterparty": "B", "type": "вихідний", "amount": 600.0},
    ]
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(svc, "payments_between", lambda a, b: payments)
        report = svc.vat_report(today, today)
    finally:
        monkey.undo()
    assert report["income"] == 1200.0
    assert report["income_vat"] == pytest.approx(200.0)  # 1200 / 6
    assert report["expense_vat"] == pytest.approx(100.0)
    assert report["net_vat"] == pytest.approx(100.0)


# ── 5.2-4: ціни постачальників ──


def test_parse_price_variants():
    from ventilation_company.services import supplier_prices_service as svc

    assert svc._parse_price("1250,50") == 1250.50
    assert svc._parse_price("1 250.50 ₴") == 1250.50
    assert svc._parse_price(99) == 99.0
    assert svc._parse_price("—") is None
    assert svc._parse_price("") is None


def test_parse_price_file_csv(tmp_path):
    from ventilation_company.services import supplier_prices_service as svc

    csv_path = tmp_path / "прайс.csv"
    csv_path.write_text(
        "Найменування;Ціна;Постачальник;Дата\n"
        "Оцинкована сталь 0.7;1250,50;Металл-ЮА;01.10.2026\n"
        "Нержавійка 1.0;2450.00;Сталь-Київ;\n"
        ";999;Без назви;\n"  # без назви — пропустити
        "Мідь;abc;Х;\n",  # ціна не число — пропустити
        encoding="utf-8",
    )
    entries = svc.parse_price_file(str(csv_path))
    assert len(entries) == 2
    assert entries[0]["name"] == "Оцинкована сталь 0.7"
    assert entries[0]["price"] == 1250.50
    assert entries[0]["supplier"] == "Металл-ЮА"
    assert entries[0]["date"] == date(2026, 10, 1)
    assert entries[1]["date"] == date.today()


def test_parse_price_file_bad_headers(tmp_path):
    from ventilation_company.services import supplier_prices_service as svc

    csv_path = tmp_path / "прайс.csv"
    csv_path.write_text("Колонка1;Колонка2\nа;1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="назва"):
        svc.parse_price_file(str(csv_path))

    with pytest.raises(ValueError, match="Підтримуються"):
        svc.parse_price_file(str(tmp_path / "прайс.pdf"))


def test_import_prices_detects_increase(monkeypatch):
    from ventilation_company.database.repositories import purchase_price_repo
    from ventilation_company.services import supplier_prices_service as svc

    recorded: list[dict] = []

    def fake_record(item_name, price, supplier="", purchase_date=None, project_id=None):
        recorded.append({"name": item_name, "price": price})
        return {"id": len(recorded)}

    def fake_latest(item_name, limit=5):
        # «Метал» вже мав ціну 100 → нові 130 — здорожчання
        return [{"price": 100.0}] if item_name == "Метал" else []

    monkeypatch.setattr(
        purchase_price_repo.PurchasePriceRepository, "record", staticmethod(fake_record)
    )
    monkeypatch.setattr(
        purchase_price_repo.PurchasePriceRepository, "latest_for", staticmethod(fake_latest)
    )
    report = svc.import_prices(
        [
            {"name": "Метал", "price": 130.0, "supplier": "Постач", "date": date.today()},
            {"name": "Новий", "price": 50.0, "supplier": "", "date": date.today()},
            {"name": "", "price": 1.0},  # пропустити
        ]
    )
    assert report["recorded"] == 2
    assert report["skipped"] == 1
    assert len(report["increased"]) == 1
    assert report["increased"][0]["old"] == 100.0
    assert report["increased"][0]["new"] == 130.0


def test_price_increase_text_and_notify(monkeypatch):
    from ventilation_company.services import supplier_prices_service as svc

    increased = [{"item": "Метал", "supplier": "Постач", "old": 100.0, "new": 130.0}]
    text = svc.build_price_increase_text(increased)
    assert "Метал" in text and "100 → 130" in text and "Постач" in text

    assert svc.notify_price_increases([]) is False
    monkeypatch.setattr(svc, "cloud_backup_preferences", lambda: (False, "", ""))
    assert svc.notify_price_increases(increased) is False
    monkeypatch.setattr(svc, "cloud_backup_preferences", lambda: (True, "t", "1"))
    sent: list[str] = []
    monkeypatch.setattr(svc, "send_telegram_message", lambda t, c, x: sent.append(x) or True)
    assert svc.notify_price_increases(increased) is True and sent


# ── 5.2-5: права доступу ──


def test_workshop_role_permissions():
    from ventilation_company.auth.permissions import Permission, Role, role_permissions

    perms = role_permissions(Role.WORKSHOP)
    assert Permission.PRODUCTION_VIEW in perms
    assert Permission.PRODUCTION_EDIT in perms
    assert Permission.WAREHOUSE_VIEW in perms
    assert Permission.PROJECTS_VIEW not in perms  # цех проєктів не бачить
    assert Permission.MONEY_VIEW not in perms
    assert Permission.SETTINGS_VIEW not in perms


def test_monter_renamed_to_brigadier():
    from ventilation_company.auth.permissions import ROLE_LABELS, Role

    assert ROLE_LABELS[Role.MONTER] == "Бригадир"
    assert ROLE_LABELS[Role.WORKSHOP] == "Цех"


def test_role_label_roundtrip():
    from ventilation_company.auth.permissions import (
        ROLE_LABELS,
        Role,
        role_label_to_value,
    )

    for role in Role:
        assert role_label_to_value(ROLE_LABELS[role]) == role.value
    assert role_label_to_value("Невідома роль") == Role.VIEWER.value


def test_tab_permissions_covers_all_roles_needed():
    from ventilation_company.auth.permissions import TAB_PERMISSIONS

    assert "production" in TAB_PERMISSIONS


def test_production_tab_disables_actions_for_viewer(qapp):
    from types import SimpleNamespace

    from PySide6.QtWidgets import QPushButton

    from ventilation_company.gui_pyside6 import production_tab as tab_module
    from ventilation_company.services import production_service

    monkey = pytest.MonkeyPatch()
    monkey.setattr(production_service, "sorted_queue", lambda status=None: [])
    monkey.setattr(
        production_service,
        "summary",
        lambda t, now=None: {
            "counts": {"в черзі": 0, "в роботі": 0, "готово": 0},
            "overdue": [],
        },
    )
    monkey.setattr(tab_module.ProjectRepository, "list_all", staticmethod(lambda: []))
    try:
        viewer = SimpleNamespace(role="viewer", full_name="Тест")
        tab = tab_module.ProductionTab(current_user=viewer)
        assert tab._can_edit() is False
        buttons = tab.findChildren(QPushButton)
        assert buttons, "у вкладці мають бути кнопки дій"
        assert all(not b.isEnabled() for b in buttons), "роль «перегляд» не редагує чергу"

        admin = SimpleNamespace(role="admin", full_name="Адмін")
        tab2 = tab_module.ProductionTab(current_user=admin)
        assert tab2._can_edit() is True
        assert all(b.isEnabled() for b in tab2.findChildren(QPushButton))
    finally:
        monkey.undo()
