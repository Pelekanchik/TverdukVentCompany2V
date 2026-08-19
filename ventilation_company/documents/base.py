"""Базовий клас для українських бухгалтерських документів."""

import os
from abc import ABC, abstractmethod
from datetime import datetime

from fpdf import FPDF

from ventilation_company.documents.company_info import CompanyInfo
from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("documents")


class BaseDocument(FPDF, ABC):
    """Базовий клас PDF-документа з підтримкою кирилиці."""

    def __init__(self, company: CompanyInfo, client: CompanyInfo, title: str = ""):
        super().__init__(unit="mm", format="A4")
        self.company = company
        self.client = client
        self.doc_title = title
        self.doc_number = ""
        self.doc_date = datetime.now().strftime("%d.%m.%Y")
        self.set_auto_page_break(auto=True, margin=15)
        # Реєструємо Unicode-шрифт (системний з кирилицею)
        try:
            from ventilation_company.pdf_generator import _find_fonts
            regular, bold = _find_fonts()
            self.add_font("DejaVu", "", regular, uni=True)
            self.add_font("DejaVu", "B", bold, uni=True)
        except Exception as exc:
            _logger.warning("Не вдалося завантажити Unicode-шрифт: %s. PDF може не відображати кирилицю.", exc)

    def header(self):
        """Заголовок кожної сторінки."""
        pass  # перевизначається в підкласах

    def footer(self):
        """Нижній колонтитул."""
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Сторінка {self.page_no()}", align="C")

    def _draw_company_block(self, label: str, info: CompanyInfo, x: float, y: float, w: float):
        """Намалювати блок з реквізитами компанії."""
        self.set_xy(x, y)
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(0, 0, 0)
        self.cell(w, 5, label, ln=True)

        self.set_font("DejaVu", "", 9)
        lines = [
            info.name,
            f"ЄДРПОУ: {info.edrpou}",
            info.address,
            f"тел.: {info.phone}" if info.phone else "",
            f"{info.bank_name}, р/р {info.bank_account}" if info.bank_account else "",
        ]
        for line in lines:
            if line:
                self.set_x(x)
                self.cell(w, 4.5, line, ln=True)

    def _draw_table_header(self, headers: list[str], widths: list[float], y: float):
        """Намалювати заголовок таблиці."""
        self.set_xy(10, y)
        self.set_fill_color(230, 230, 230)
        self.set_font("DejaVu", "B", 9)
        for header, width in zip(headers, widths):
            self.cell(width, 7, header, border=1, align="C", fill=True)
        self.ln()

    def _draw_table_row(self, cells: list[str], widths: list[float], align: str = "C"):
        """Намалювати рядок таблиці."""
        self.set_font("DejaVu", "", 9)
        for cell, width in zip(cells, widths):
            self.cell(width, 6, str(cell), border=1, align=align)
        self.ln()

    def _draw_totals(self, subtotal: float, vat_rate: float = 20.0):
        """Намалювати блок підсумків."""
        from decimal import Decimal
        from ventilation_company.utils.money import money_round

        d_subtotal = money_round(subtotal)
        d_vat = money_round(Decimal(str(subtotal)) * Decimal(str(vat_rate)) / Decimal('100'))
        d_total = d_subtotal + d_vat

        self.set_font("DejaVu", "B", 10)
        self.cell(0, 8, f"Разом без ПДВ: {d_subtotal} грн", ln=True, align="R")
        self.cell(0, 8, f"ПДВ ({vat_rate}%): {d_vat} грн", ln=True, align="R")
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, f"ВСЬОГО ДО СПЛАТИ: {d_total} грн", ln=True, align="R")

        # Прописом
        self.set_font("DejaVu", "", 9)
        self.cell(0, 6, f"( {self._number_to_words(d_total)} )", ln=True, align="R")

    def _number_to_words(self, amount) -> str:
        """Сума прописом (спрощено)."""
        # TODO: повна реалізація українською
        return f"{amount} грн 00 коп."

    def _draw_signatures(self, y: float):
        """Намалювати блок підписів."""
        self.set_y(y)
        self.set_font("DejaVu", "", 10)

        self.cell(90, 8, f"Від постачальника: {self.company.director}", ln=False)
        self.cell(0, 8, f"Від замовника: _________________", ln=True)

        self.cell(90, 8, "_________________ / підпис /", ln=False)
        self.cell(0, 8, "_________________ / підпис /", ln=True)

    @abstractmethod
    def build(self, items: list[dict], filepath: str) -> str:
        """Побудувати документ і зберегти.

        items: список {name, unit, qty, price, total}
        Повертає шлях до збереженого файлу.
        """
        pass
