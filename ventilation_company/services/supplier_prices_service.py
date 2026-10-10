"""Ціни постачальників (розділ 5.2): імпорт прайсів, історія, алерти.

Імпорт прайсу постачальника з CSV або Excel (XLSX): назва позиції,
ціна, необов'язково постачальник і дата. Кожен імпорт додається
в історію цін (PurchasePriceRepository). Якщо нова ціна вища за
останню зафіксовану — позиція потрапляє в список «здорожчань»,
який можна одразу надіслати в Telegram.
"""

from __future__ import annotations

import csv
from datetime import date, datetime

from ventilation_company.database.repositories.purchase_price_repo import (
    PurchasePriceRepository,
)
from ventilation_company.utils.cloud_backup import (
    cloud_backup_preferences,
    send_telegram_message,
)

# Відповідність заголовків колонок (нижній регістр, без зайвих пробілів).
_NAME_HEADERS = {
    "найменування",
    "назва",
    "матеріал",
    "товар",
    "позиція",
    "name",
    "item",
    "material",
}
_PRICE_HEADERS = {"ціна", "цiна", "цена", "вартість", "price", "cost"}
_SUPPLIER_HEADERS = {"постачальник", "постачальники", "supplier", "vendor"}
_DATE_HEADERS = {"дата", "date"}


def _norm_header(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _parse_price(value) -> float | None:
    """Парсинг ціни: кома або крапка як роздільник, пробіли/₴ відкидаються."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("₴", "").replace(" ", "").replace("\u00a0", "")
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value) -> date | None:
    if value is None or isinstance(value, date):
        return value if not isinstance(value, datetime) else value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def _map_columns(headers: list[str]) -> dict[str, int] | None:
    """Знайти індекси колонок за заголовками; None — немає колонки ціни/назви."""
    mapping: dict[str, int] = {}
    for idx, raw in enumerate(headers):
        header = _norm_header(raw)
        if header in _NAME_HEADERS and "name" not in mapping:
            mapping["name"] = idx
        elif header in _PRICE_HEADERS and "price" not in mapping:
            mapping["price"] = idx
        elif header in _SUPPLIER_HEADERS and "supplier" not in mapping:
            mapping["supplier"] = idx
        elif header in _DATE_HEADERS and "date" not in mapping:
            mapping["date"] = idx
    if "name" not in mapping or "price" not in mapping:
        return None
    return mapping


def parse_price_file(path: str) -> list[dict]:
    """Розпарсити CSV або XLSX: рядки {name, price, supplier, date}.

    Порожні рядки та рядки без назви/ціни пропускаються.
    Винятки (немає колонок назви/ціни, невідомий формат) — ValueError.
    """
    lowered = path.lower()
    if lowered.endswith((".xlsx", ".xlsm")):
        rows = _read_xlsx(path)
    elif lowered.endswith(".csv"):
        rows = _read_csv(path)
    else:
        raise ValueError("Підтримуються лише файли .csv та .xlsx")
    if not rows:
        return []
    mapping = _map_columns([str(h) for h in rows[0]])
    if mapping is None:
        raise ValueError(
            "Не знайдено колонок «назва» і «ціна» (допустимі заголовки: "
            "найменування/назва/матеріал/tovar/name; ціна/вартість/price)"
        )
    entries = []
    for raw in rows[1:]:
        cells = [str(c).strip() if c is not None else "" for c in raw]
        name = cells[mapping["name"]] if mapping["name"] < len(cells) else ""
        if not name:
            continue
        price_raw = raw[mapping["price"]] if mapping["price"] < len(raw) else ""
        price = _parse_price(price_raw)
        if price is None:
            continue
        supplier = (
            cells[mapping["supplier"]]
            if "supplier" in mapping and mapping["supplier"] < len(cells)
            else ""
        )
        entry_date = None
        if "date" in mapping and mapping["date"] < len(raw):
            entry_date = _parse_date(raw[mapping["date"]])
        entries.append(
            {
                "name": name,
                "price": price,
                "supplier": supplier,
                "date": entry_date or date.today(),
            }
        )
    return entries


def _read_csv(path: str) -> list[list]:
    for encoding in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            with open(path, newline="", encoding=encoding) as f:
                sample = f.read(4096)
                f.seek(0)
                delimiter = ";" if sample.count(";") >= sample.count(",") else ","
                return [row for row in csv.reader(f, delimiter=delimiter)]
        except UnicodeDecodeError:
            continue
    raise ValueError("Не вдалося прочитати CSV (невідоме кодування)")


def _read_xlsx(path: str) -> list[list]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise ValueError("Для читання XLSX потрібен пакет openpyxl") from exc
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [list(row) for row in ws.iter_rows(values_only=True)]
    wb.close()
    return rows


def import_prices(entries: list[dict]) -> dict:
    """Записати історію цін; виявити здорожчання vs остання ціна.

    Повертає {"recorded": int, "increased": [{item, supplier, old, new}],
    "skipped": int}. Дрібні зміни (< 0.1 %) не вважаються здорожчанням.
    """
    recorded = skipped = 0
    increased: list[dict] = []
    for entry in entries:
        name = (entry.get("name") or "").strip()
        price = entry.get("price")
        if not name or price is None:
            skipped += 1
            continue
        previous = PurchasePriceRepository.latest_for(name, limit=1)
        old_price = previous[0]["price"] if previous else None
        PurchasePriceRepository.record(
            item_name=name,
            price=float(price),
            supplier=entry.get("supplier") or "",
            purchase_date=entry.get("date"),
        )
        recorded += 1
        if old_price is not None and float(price) > old_price * 1.001:
            increased.append(
                {
                    "item": name,
                    "supplier": entry.get("supplier") or "",
                    "old": old_price,
                    "new": float(price),
                }
            )
    return {"recorded": recorded, "increased": increased, "skipped": skipped}


def build_price_increase_text(increased: list[dict]) -> str:
    """Текст дайджесту здорожчань для Telegram."""
    lines = ["📈 Ціни постачальників зросли — VentCompany", ""]
    for row in increased:
        supplier = f" ({row['supplier']})" if row.get("supplier") else ""
        lines.append(
            f"• {row['item']}{supplier}: {row['old']:g} → {row['new']:g} ₴"
            f" (+{row['new'] - row['old']:g})"
        )
    lines.append("")
    lines.append(f"🕒 {datetime.now():%d.%m.%Y %H:%M}")
    return "\n".join(lines)


def notify_price_increases(increased: list[dict]) -> bool:
    """Надіслати дайджест здорожчань у Telegram; False — нічого/нема бота."""
    if not increased:
        return False
    _enabled, token, chat = cloud_backup_preferences()
    if not token or not chat:
        return False
    return send_telegram_message(token, chat, build_price_increase_text(increased))
