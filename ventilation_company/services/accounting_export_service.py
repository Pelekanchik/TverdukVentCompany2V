"""Експорт для бухгалтерії (розділ 5.2): виписка оплат та звіт по ПДВ.

Формати:
  • CSV (UTF-8 з BOM) — відкривається в Excel: дата, контрагент, тип,
    сума, валюта, призначення, проєкт, примітка
  • «1С:Клієнт банку» (TXT) — стандартний обмінний формат
    1СClientBankExchange для імпорту виписки в 1С

Звіт по ПДВ: ставка 20 % (ПДВ = сума × 20/120 = сума / 6) окремо
по надходженнях (зобов'язання) і витратах (податковий кредит).
"""

from __future__ import annotations

import csv
from datetime import date, datetime

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.database.repositories.payment_repo import PaymentRepository

VAT_FRACTION = 20 / 120  # ПДВ 20 % «в тому числі»

CSV_HEADER = [
    "Дата",
    "Контрагент",
    "Тип",
    "Сума",
    "Валюта",
    "Призначення",
    "Проєкт",
    "Примітка",
]


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return None


def payments_between(date_from: date, date_to: date) -> list[dict]:
    """Оплати за період із іменами контрагентів, відсортовані за датою."""
    rows = []
    for p in PaymentRepository.list_all() or []:
        d = _as_date(p.get("date"))
        if d is None or not (date_from <= d <= date_to):
            continue
        client_name = ""
        if p.get("client_id"):
            try:
                client = ClientRepository.get(p["client_id"]) or {}
                client_name = client.get("name") or ""
            except Exception:  # noqa: BLE001 — ім'я не критичне
                client_name = ""
        rows.append(
            {
                "date": d,
                "counterparty": client_name or "—",
                "type": p.get("type") or "вхідний",
                "amount": float(p.get("amount") or 0),
                "currency": p.get("currency") or "UAH",
                "purpose": p.get("purpose") or "",
                "project": p.get("project_name") or "",
                "notes": (p.get("notes") or "").replace("\n", " "),
            }
        )
    rows.sort(key=lambda r: (r["date"], r["type"]))
    return rows


def export_payments_csv(payments: list[dict], path: str) -> str:
    """CSV-виписка для Excel/бухгалтерії. Повертає шлях."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADER)
        for p in payments:
            writer.writerow(
                [
                    f"{p['date']:%d.%m.%Y}",
                    p["counterparty"],
                    "Надходження" if p["type"] == "вхідний" else "Витрата",
                    f"{p['amount']:.2f}".replace(".", ","),
                    p["currency"],
                    p["purpose"],
                    p["project"],
                    p["notes"],
                ]
            )
    return path


def export_payments_1c(payments: list[dict], path: str, account: str = "") -> str:
    """Виписка у форматі обміну «1С:Клієнт банку» (1CClientBankExchange)."""
    now = datetime.now()
    lines = [
        "1CClientBankExchange",
        "ВерсияФормата=1.02",
        "Кодировка=Windows",
        "Отправитель=VentCompany",
        "Получатель=1С:Підприємство",
        f"ДатаСоздания={now:%d.%m.%Y}",
        f"ВремяСоздания={now:%H:%M:%S}",
        "",
        "СекцияРасчСчет",
        f"РасчСчет={account}",
        f"ВсегоПоступило={sum(p['amount'] for p in payments if p['type'] == 'вхідний'):.2f}",
        f"ВсегоСписано={sum(p['amount'] for p in payments if p['type'] != 'вхідний'):.2f}",
        "КонецРасчСчет",
        "",
    ]
    for number, p in enumerate(payments, 1):
        direction_in = p["type"] == "вхідний"
        lines += [
            "СекцияПлатежноеПоручение",
            f"Номер={number}",
            f"Дата={p['date']:%d.%m.%Y}",
            f"Сумма={p['amount']:.2f}",
            f"{'Плательщик' if direction_in else 'Получатель'}={p['counterparty']}",
            f"НазначениеПлатежа={p['purpose'] or p['project'] or 'Оплата'}",
            "КонецПлатежногоПоручения",
            "",
        ]
    lines.append("КонецФайла")
    with open(path, "w", encoding="cp1251", errors="replace") as f:
        f.write("\n".join(lines))
    return path


def vat_report(date_from: date, date_to: date) -> dict:
    """Звіт по ПДВ за період (ставка 20 %, «в тому числі»).

    Повертає суми надходжень/витрат і відповідний ПДВ,
    а також ПДВ до сплати (зобов'язання − кредит).
    """
    payments = payments_between(date_from, date_to)
    income = sum(p["amount"] for p in payments if p["type"] == "вхідний")
    expense = sum(p["amount"] for p in payments if p["type"] != "вхідний")
    income_vat = income * VAT_FRACTION
    expense_vat = expense * VAT_FRACTION
    return {
        "income": income,
        "income_vat": income_vat,
        "expense": expense,
        "expense_vat": expense_vat,
        "net_vat": income_vat - expense_vat,
        "payments_count": len(payments),
    }


def export_vat_csv(report: dict, date_from: date, date_to: date, path: str) -> str:
    """Зберегти звіт по ПДВ у CSV (дві колонки: показник, сума)."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Звіт по ПДВ", f"{date_from:%d.%m.%Y} — {date_to:%d.%m.%Y}"])
        writer.writerow([])
        rows = [
            ("Операцій за період", str(report["payments_count"])),
            ("Надходження (без ПДВ, факт)", f"{report['income']:.2f}"),
            ("ПДВ зобов'язання (20 %)", f"{report['income_vat']:.2f}"),
            ("Витрати (факт)", f"{report['expense']:.2f}"),
            ("Податковий кредит (20 %)", f"{report['expense_vat']:.2f}"),
            ("ПДВ до сплати", f"{report['net_vat']:.2f}"),
        ]
        writer.writerows(rows)
    return path
