"""Генератор Комерційної Пропозиції (КП) у PDF.

Красивий PDF з:
  • титульною сторінкою (логотип, контакти)
  • таблицею обладнання/виробів з цінами
  • термінами виконання
  • гарантією
  • умовами оплати
  • підписами
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("Бібліотека fpdf2 не встановлена. Виконайте: pip install fpdf2")


_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
]

_FONT_CANDIDATES_LINUX = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


def _find_fonts() -> tuple[str, str]:
    for regular, bold in _FONT_CANDIDATES + _FONT_CANDIDATES_LINUX:
        if os.path.exists(regular) and os.path.exists(bold):
            return regular, bold
    raise RuntimeError("Не знайдено системний шрифт з підтримкою кирилиці.")


def _clean(text) -> str:
    if text is None:
        return ""
    return str(text).replace("\n", " ").replace("\r", " ").replace("\t", " ")


@dataclass
class ProposalItem:
    """Один рядок у таблиці КП."""
    name: str
    description: str = ""
    quantity: float = 1.0
    unit: str = "шт"
    price_per_unit: float = 0.0
    total: float = 0.0


@dataclass
class ProposalData:
    """Дані для КП."""
    # Фірма
    company_name: str = "ТОВ «ВентКомпані»"
    company_address: str = "м. Київ, вул. Промислова, 15"
    company_phone: str = "+38 (044) 123-45-67"
    company_email: str = "info@ventcompany.ua"
    company_website: str = "www.ventcompany.ua"
    company_edrpou: str = "12345678"
    company_logo_path: str = ""

    # Клієнт
    client_name: str = ""
    client_contact: str = ""
    client_phone: str = ""
    client_address: str = ""

    # Проєкт
    project_name: str = ""
    project_number: str = ""
    proposal_number: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%d.%m.%Y"))
    valid_until: str = field(default_factory=lambda: (datetime.now() + timedelta(days=30)).strftime("%d.%m.%Y"))

    # Зміст
    items: List[ProposalItem] = field(default_factory=list)
    delivery_days: int = 14
    installation_days: int = 7
    warranty_months: int = 24
    payment_terms: str = "50% аванс, 50% після монтажу"
    notes: str = ""

    # Підсумки
    subtotal: float = 0.0
    vat_percent: float = 20.0
    vat_amount: float = 0.0
    total: float = 0.0


class ProposalPDF(FPDF):
    """PDF-документ Комерційної Пропозиції."""

    def __init__(self, data: ProposalData):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.data = data
        self.regular_font, self.bold_font = _find_fonts()
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font("Main", "", self.regular_font, uni=True)
        self.add_font("Main", "B", self.bold_font, uni=True)
        self._build()

    def _set_regular(self, size: int = 10):
        self.set_font("Main", "", size)

    def _set_bold(self, size: int = 10):
        self.set_font("Main", "B", size)

    def _color(self, r: int, g: int, b: int):
        self.set_text_color(r, g, b)

    def _build(self):
        self.add_page()
        self._page_header()
        self._page_title()
        self._client_info()
        self._items_table()
        self._totals()
        self._terms()
        self._signatures()
        self._footer()

    def _page_header(self):
        """Шапка з логотипом і контактами."""
        # Фонова смуга
        self.set_fill_color(21, 101, 192)
        self.rect(0, 0, 210, 35, style="F")

        # Логотип (placeholder або зображення)
        if self.data.company_logo_path and os.path.exists(self.data.company_logo_path):
            try:
                self.image(self.data.company_logo_path, x=10, y=5, w=25)
            except Exception:
                pass
        else:
            self._set_bold(16)
            self.set_text_color(255, 255, 255)
            self.set_xy(10, 10)
            self.cell(0, 8, _clean(self.data.company_name), ln=False)

        # Контакти праворуч
        self._set_regular(8)
        self.set_text_color(255, 255, 255)
        self.set_xy(120, 8)
        self.cell(80, 5, f"📍 {_clean(self.data.company_address)}", align="R", ln=True)
        self.set_x(120)
        self.cell(80, 5, f"📞 {_clean(self.data.company_phone)}", align="R", ln=True)
        self.set_x(120)
        self.cell(80, 5, f"✉ {_clean(self.data.company_email)}", align="R", ln=True)
        self.set_x(120)
        self.cell(80, 5, f"🌐 {_clean(self.data.company_website)}", align="R", ln=True)

        self.ln(20)

    def _page_title(self):
        """Заголовок КП."""
        self._set_bold(20)
        self._color(21, 101, 192)
        self.cell(0, 12, "КОМЕРЦІЙНА ПРОПОЗИЦІЯ", align="C", ln=True)

        self._set_regular(10)
        self._color(100, 100, 100)
        self.cell(0, 6, f"№ {_clean(self.data.proposal_number)} від {_clean(self.data.date)}", align="C", ln=True)
        self.cell(0, 6, f"Дійсна до: {_clean(self.data.valid_until)}", align="C", ln=True)
        self.ln(4)

    def _client_info(self):
        """Інформація про клієнта та проєкт."""
        # Ліва колонка — клієнт
        self._set_bold(11)
        self._color(21, 101, 192)
        self.cell(95, 7, "Клієнт:", ln=False)
        self.cell(0, 7, "Проєкт:", ln=True)

        self._set_regular(10)
        self._color(50, 50, 50)

        # Клієнт
        x = self.get_x()
        y = self.get_y()
        self.set_xy(x, y)
        self.cell(95, 6, f"  {_clean(self.data.client_name)}", ln=False)
        self.cell(0, 6, f"  {_clean(self.data.project_name)}", ln=True)

        if self.data.client_contact:
            self.cell(95, 6, f"  Контакт: {_clean(self.data.client_contact)}", ln=False)
        if self.data.project_number:
            self.cell(0, 6, f"  №: {_clean(self.data.project_number)}", ln=True)
        else:
            self.ln(6)

        if self.data.client_address:
            self.cell(95, 6, f"  Адреса: {_clean(self.data.client_address)}", ln=False)
        if self.data.client_phone:
            self.cell(0, 6, f"  Тел: {_clean(self.data.client_phone)}", ln=True)
        else:
            self.ln(6)

        self.ln(3)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def _items_table(self):
        """Таблиця з виробами/обладнанням."""
        if not self.data.items:
            self._set_regular(10)
            self._color(150, 150, 150)
            self.cell(0, 8, "(позиції не додано)", align="C", ln=True)
            self.ln(3)
            return

        self._set_bold(11)
        self._color(21, 101, 192)
        self.cell(0, 8, "ПЕРЕЛІК ОБЛАДНАННЯ ТА ВИРОБІВ", ln=True)
        self.ln(1)

        # Заголовок таблиці
        self.set_fill_color(21, 101, 192)
        self.set_text_color(255, 255, 255)
        self._set_bold(9)

        col_w = [10, 65, 20, 20, 25, 25, 25]  # №, Найменування, Од., К-ть, Ціна, Сума
        headers = ["№", "Найменування", "Од.", "К-ть", "Ціна, грн", "Сума, грн"]
        for w, h in zip(col_w, headers):
            self.cell(w, 8, h, border=0, align="C", fill=True)
        self.ln()

        # Рядки
        self.set_text_color(50, 50, 50)
        self._set_regular(9)
        fill = False
        for i, item in enumerate(self.data.items, 1):
            if fill:
                self.set_fill_color(240, 248, 255)
            else:
                self.set_fill_color(255, 255, 255)

            h = 8
            # Перевірка, чи треба нову сторінку
            if self.get_y() + h > 270:
                self.add_page()
                self._page_header()
                self.set_fill_color(21, 101, 192)
                self.set_text_color(255, 255, 255)
                self._set_bold(9)
                for w, h_text in zip(col_w, headers):
                    self.cell(w, 8, h_text, border=0, align="C", fill=True)
                self.ln()
                self.set_text_color(50, 50, 50)
                self._set_regular(9)

            self.cell(col_w[0], h, str(i), border="TB", align="C", fill=True)
            self.cell(col_w[1], h, _clean(item.name), border="TB", align="L", fill=True)
            self.cell(col_w[2], h, _clean(item.unit), border="TB", align="C", fill=True)
            self.cell(col_w[3], h, f"{item.quantity:.0f}", border="TB", align="C", fill=True)
            self.cell(col_w[4], h, f"{item.price_per_unit:,.2f}", border="TB", align="R", fill=True)
            self.cell(col_w[5], h, f"{item.total:,.2f}", border="TB", align="R", fill=True)
            self.ln()
            fill = not fill

        # Нижня лінія
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def _totals(self):
        """Підсумкові суми."""
        self.set_x(120)
        self._set_regular(10)
        self._color(80, 80, 80)
        self.cell(40, 7, "Всього без ПДВ:", align="R", ln=False)
        self._set_bold(10)
        self.cell(40, 7, f"{self.data.subtotal:,.2f} грн", align="R", ln=True)

        self.set_x(120)
        self._set_regular(10)
        self.cell(40, 7, f"ПДВ {self.data.vat_percent:.0f}%:", align="R", ln=False)
        self._set_bold(10)
        self.cell(40, 7, f"{self.data.vat_amount:,.2f} грн", align="R", ln=True)

        self.set_x(120)
        self.set_fill_color(21, 101, 192)
        self.set_text_color(255, 255, 255)
        self._set_bold(12)
        self.cell(40, 10, "ВСЬОГО:", align="R", fill=True, ln=False)
        self.cell(40, 10, f"{self.data.total:,.2f} грн", align="R", fill=True, ln=True)

        self.set_text_color(50, 50, 50)
        self.ln(5)

    def _terms(self):
        """Умови: терміни, гарантія, оплата."""
        self._set_bold(11)
        self._color(21, 101, 192)
        self.cell(0, 8, "УМОВИ ПОСТАВКИ", ln=True)
        self.ln(1)

        self._set_regular(10)
        self._color(50, 50, 50)

        terms = [
            ("⏱️ Термін виготовлення:", f"{self.data.delivery_days} робочих днів"),
            ("🔧 Термін монтажу:", f"{self.data.installation_days} робочих днів"),
            ("🛡️ Гарантія:", f"{self.data.warranty_months} місяців"),
            ("💳 Умови оплати:", _clean(self.data.payment_terms)),
        ]

        for label, value in terms:
            self._set_bold(10)
            self.cell(65, 7, label, ln=False)
            self._set_regular(10)
            self.cell(0, 7, value, ln=True)

        if self.data.notes:
            self.ln(2)
            self._set_bold(10)
            self.cell(0, 7, "Примітки:", ln=True)
            self._set_regular(9)
            self._color(80, 80, 80)
            self.multi_cell(0, 5, _clean(self.data.notes))

        self.ln(5)

    def _signatures(self):
        """Підписи."""
        self._set_bold(11)
        self._color(21, 101, 192)
        self.cell(0, 8, "ПІДПИСИ", ln=True)
        self.ln(2)

        self._set_regular(10)
        self._color(50, 50, 50)

        y = self.get_y()
        # Від постачальника
        self.cell(95, 7, "Від постачальника:", ln=False)
        self.cell(0, 7, "Від замовника:", ln=True)

        self.cell(95, 7, f"{_clean(self.data.company_name)}", ln=False)
        self.cell(0, 7, f"{_clean(self.data.client_name)}", ln=True)

        self.ln(8)
        self.set_draw_color(100, 100, 100)
        self.line(10, self.get_y(), 80, self.get_y())
        self.line(120, self.get_y(), 190, self.get_y())
        self.ln(2)
        self._set_regular(8)
        self._color(120, 120, 120)
        self.cell(95, 5, "підпис / М.П.", align="C", ln=False)
        self.cell(0, 5, "підпис / М.П.", align="C", ln=True)

    def _footer(self):
        """Нижній колонтитул."""
        self.set_y(-15)
        self._set_regular(8)
        self._color(128, 128, 128)
        self.cell(0, 10, f"Сторінка {self.page_no()}  |  {_clean(self.data.company_name)}  |  {_clean(self.data.company_phone)}", align="C")

    def save(self, output_path: str) -> str:
        self.output(output_path)
        return output_path


def generate_proposal(project_data: dict, items: List[dict], output_path: str) -> str:
    """Швидка функція для генерації КП з даних проєкту."""
    prop = ProposalData()

    # Заповнюємо з project_data
    prop.project_name = project_data.get("name", "")
    prop.project_number = project_data.get("project_number", "")
    prop.client_name = project_data.get("client", "")
    prop.client_address = project_data.get("address", "")
    prop.proposal_number = project_data.get("proposal_number", f"KP-{datetime.now().strftime("%Y%m%d")}-001")

    # Позиції
    prop.items = []
    subtotal = 0.0
    for it in items:
        qty = float(it.get("quantity", 1))
        price = float(it.get("price", 0))
        total = qty * price
        subtotal += total
        prop.items.append(ProposalItem(
            name=it.get("name", ""),
            description=it.get("description", ""),
            quantity=qty,
            unit=it.get("unit", "шт"),
            price_per_unit=price,
            total=total,
        ))

    prop.subtotal = round(subtotal, 2)
    prop.vat_amount = round(subtotal * prop.vat_percent / 100, 2)
    prop.total = round(prop.subtotal + prop.vat_amount, 2)

    # Терміни
    prop.delivery_days = project_data.get("delivery_days", 14)
    prop.installation_days = project_data.get("installation_days", 7)
    prop.warranty_months = project_data.get("warranty_months", 24)
    prop.payment_terms = project_data.get("payment_terms", "50% аванс, 50% після монтажу")
    prop.notes = project_data.get("notes", "")

    pdf = ProposalPDF(prop)
    pdf.save(output_path)
    return output_path
