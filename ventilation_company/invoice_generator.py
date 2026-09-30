"""Генератор рахунка на оплату (PDF).

Документ для оплати замовником: реквізити фірми з банківськими даними,
постачальник/платник, перелік робіт/виробів, суми з ПДВ, призначення
платежу. Реквізити фірми (Виконавця) підставляються з
«Налаштування → Бізнес» (services/business_settings.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ventilation_company.act_generator import ActItem, amount_in_words
from ventilation_company.proposal_generator import _clean, _find_fonts

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("Бібліотека fpdf2 не встановлена. Виконайте: pip install fpdf2") from None


@dataclass
class InvoiceData:
    """Дані для рахунка на оплату."""

    # Фірма (Постачальник)
    company_name: str = "ТОВ «ВентКомпані»"
    company_address: str = "м. Київ, вул. Промислова, 15"
    company_phone: str = "+38 (044) 123-45-67"
    company_email: str = "info@ventcompany.ua"
    company_edrpou: str = "12345678"
    company_signatory: str = "Директор Іваненко І.І."
    bank_name: str = "АТ «Ощадбанк»"
    iban: str = "UA00 0000 0000 0000 0000 0000 00"
    mfo: str = "300465"

    # Клієнт (Платник)
    client_name: str = ""
    client_address: str = ""

    # Рахунок
    invoice_number: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%d.%m.%Y"))
    contract_number: str = ""
    project_name: str = ""
    project_number: str = ""
    items: list[ActItem] = field(default_factory=list)
    vat_percent: float = 20.0
    notes: str = ""


class InvoicePDF(FPDF):
    """PDF-документ рахунка на оплату."""

    def __init__(self, data: InvoiceData):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.data = data
        self.regular_font, self.bold_font = _find_fonts()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        self.add_font("Main", "", self.regular_font)
        self.add_font("Main", "B", self.bold_font)
        self._build()

    # ── Шрифти ──

    def _regular(self, size: int = 10):
        self.set_font("Main", "", size)

    def _bold(self, size: int = 10):
        self.set_font("Main", "B", size)

    def _mc(self, h: float, text: str, align: str = "L"):
        """Текстовий блок: завжди з лівого поля, після — новий рядок зліва."""
        self.set_x(self.l_margin)
        self.multi_cell(170, h, text, align=align, new_x="LMARGIN", new_y="NEXT")

    # ── Побудова ──

    def _build(self):
        self.add_page()
        self._bank_block()
        self._title()
        self._parties()
        self._items_table()
        self._totals()
        self._payment_purpose()
        self._signatures()

    def _bank_block(self):
        """Банківські реквізити постачальника у рамці."""
        self._regular(9)
        lines = [
            _clean(self.data.company_name),
            f"ЄДРПОУ {_clean(self.data.company_edrpou)}",
            f"Банк: {_clean(self.data.bank_name)}",
            f"IBAN: {_clean(self.data.iban)}",
            f"МФО: {_clean(self.data.mfo)}",
            f"Адреса: {_clean(self.data.company_address)}",
            f"Тел.: {_clean(self.data.company_phone)}  E-mail: {_clean(self.data.company_email)}",
        ]
        text = "\n".join(lines)
        self.set_x(self.l_margin)
        self.multi_cell(170, 5, text, border=1, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def _title(self):
        self._bold(14)
        self._mc(
            8,
            f"РАХУНОК на оплату № {_clean(self.data.invoice_number)}",
            align="C",
        )
        self._bold(10)
        self._mc(6, f"від «{_clean(self.data.date)}»", align="C")
        self.ln(2)

    def _parties(self):
        self._regular(10)
        provider = (
            f"ПОСТАЧАЛЬНИК: {_clean(self.data.company_name)}, "
            f"ЄДРПОУ {_clean(self.data.company_edrpou)}, "
            f"{_clean(self.data.company_address)}"
        )
        payer = f"ПЛАТНИК: {_clean(self.data.client_name) or '____________________'}" + (
            f", {_clean(self.data.client_address)}" if self.data.client_address else ""
        )
        self._mc(5.5, provider)
        self._mc(5.5, payer)
        basis = (
            f"Підстава: договір № {_clean(self.data.contract_number)}"
            if self.data.contract_number
            else "Підстава: ____________________"
        )
        if self.data.project_name:
            basis += f", проєкт «{_clean(self.data.project_name)}»"
        self._mc(5.5, basis)
        self.ln(2)

    def _items_table(self):
        cols = [
            ("№", 10),
            ("Найменування робіт / виробів", 78),
            ("К-ть", 16),
            ("Од.", 12),
            ("Ціна, грн", 26),
            ("Сума, грн", 28),
        ]
        header_h = 7

        def draw_header():
            self.set_x(self.l_margin)
            self._bold(9)
            self.set_fill_color(230, 230, 230)
            for title, w in cols:
                self.cell(w, header_h, title, border=1, fill=True, align="C")
            self.ln(header_h)

        draw_header()
        self._regular(9)
        for i, item in enumerate(self.data.items, 1):
            name = _clean(item.name)
            if item.description:
                name = f"{name} ({_clean(item.description)})"
            split = self.multi_cell(cols[1][1], 5, name, split_only=True)
            lines = split if isinstance(split, list) else [name]
            row_h = max(6, 5 * len(lines) + 1)
            if self.get_y() + row_h > 275:
                self.add_page()
                draw_header()
                self._regular(9)

            y = self.get_y()
            self.set_xy(self.l_margin, y)
            self.cell(cols[0][1], row_h, str(i), border=1, align="C")
            self.multi_cell(
                cols[1][1],
                5,
                name,
                border=1,
                align="L",
                new_x="RIGHT",
                new_y="TOP",
            )
            self.cell(cols[2][1], row_h, f"{item.quantity:g}", border=1, align="C")
            self.cell(cols[3][1], row_h, _clean(item.unit), border=1, align="C")
            self.cell(cols[4][1], row_h, f"{item.price_per_unit:,.2f}", border=1, align="R")
            self.cell(cols[5][1], row_h, f"{item.total:,.2f}", border=1, align="R")
            self.ln(row_h)

    def _totals(self):
        subtotal = round(sum(i.total for i in self.data.items), 2)
        vat = round(subtotal * self.data.vat_percent / 100, 2)
        total = round(subtotal + vat, 2)
        self.ln(2)
        self._regular(10)
        rows = [
            ("Разом без ПДВ:", f"{subtotal:,.2f} грн"),
            (f"ПДВ {self.data.vat_percent:.0f}%:", f"{vat:,.2f} грн"),
            ("Всього з ПДВ:", f"{total:,.2f} грн"),
        ]
        for label, value in rows:
            self.set_x(self.l_margin)
            self.cell(120, 6, label, align="R")
            self.cell(50, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self._bold(10)
        self._mc(5.5, f"Всього до сплати: {amount_in_words(total)}.")
        self._regular(10)
        if self.data.notes:
            self._mc(5, f"Примітка: {_clean(self.data.notes)}")

    def _payment_purpose(self):
        purpose = (
            f"Призначення платежу: оплата за виготовлення та монтаж вентиляційних "
            f"систем згідно рахунку № {_clean(self.data.invoice_number)}"
        )
        if self.data.contract_number:
            purpose += f" до договору № {_clean(self.data.contract_number)}"
        self.ln(2)
        self._regular(10)
        self._mc(5.5, purpose)

    def _signatures(self):
        if self.get_y() > 240:
            self.add_page()
        self.ln(8)
        col_w = 85
        self._bold(10)
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self.cell(col_w, 6, "ПОСТАЧАЛЬНИК:", new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 6, "ПЛАТНИК:", new_x="RIGHT", new_y="NEXT")
        self.ln(8)
        self._regular(10)
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self.cell(col_w, 5.5, "____________________", new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 5.5, "____________________", new_x="RIGHT", new_y="NEXT")
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self.cell(col_w, 5.5, f"{_clean(self.data.company_signatory)}", new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 5.5, "____________________", new_x="RIGHT", new_y="NEXT")
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self.cell(col_w, 5.5, "(підпис)", new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 5.5, "(підпис)", new_x="RIGHT", new_y="NEXT")


def generate_invoice(project_data: dict, items: list[dict], output_path: str) -> str:
    """Згенерувати рахунок на оплату з даних проєкту."""
    data = InvoiceData()
    data.invoice_number = project_data.get(
        "invoice_number", f"РН-{datetime.now().strftime('%Y%m%d')}-001"
    )
    data.project_name = project_data.get("name", "")
    data.project_number = project_data.get("project_number", "")
    data.client_name = project_data.get("client", "")
    data.client_address = project_data.get("address", "")
    data.contract_number = project_data.get("contract_number", "")
    if project_data.get("notes"):
        data.notes = str(project_data["notes"])

    data.items = []
    for it in items:
        qty = float(it.get("quantity", 1))
        price = float(it.get("price", 0))
        data.items.append(
            ActItem(
                name=it.get("name", ""),
                description=it.get("description", ""),
                quantity=qty,
                unit=it.get("unit", "шт"),
                price_per_unit=price,
                total=round(qty * price, 2),
            )
        )

    company = project_data.get("company") or {}
    if isinstance(company, dict):
        data.company_name = str(company.get("name") or data.company_name)
        data.company_address = str(company.get("address") or data.company_address)
        data.company_phone = str(company.get("phone") or data.company_phone)
        data.company_email = str(company.get("email") or data.company_email)
        data.company_edrpou = str(company.get("edrpou") or data.company_edrpou)
        data.company_signatory = str(company.get("signatory") or data.company_signatory)
        data.bank_name = str(company.get("bank_name") or data.bank_name)
        data.iban = str(company.get("iban") or data.iban)
        data.mfo = str(company.get("mfo") or data.mfo)

    pdf = InvoicePDF(data)
    pdf.output(output_path)
    return output_path
