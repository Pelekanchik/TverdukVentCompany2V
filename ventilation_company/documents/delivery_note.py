"""Товарна накладна (ТН)."""

from datetime import datetime

from ventilation_company.documents.base import BaseDocument
from ventilation_company.documents.company_info import CompanyInfo


class DeliveryNote(BaseDocument):
    """Товарна накладна (ТН)."""

    def __init__(self, company: CompanyInfo, client: CompanyInfo, tn_number: str = ""):
        super().__init__(company, client, title="ТОВАРНА НАКЛАДНА")
        self.doc_number = tn_number or f"ТН-{datetime.now().strftime('%Y%m%d-%H%M')}"

    def header(self):
        self.set_font("DejaVu", "B", 14)
        self.cell(0, 10, self.doc_title, ln=True, align="C")
        self.set_font("DejaVu", "", 10)
        self.cell(0, 6, f"№ {self.doc_number} від {self.doc_date}", ln=True, align="C")
        self.ln(4)

        self._draw_company_block("Вантажовідправник:", self.company, 10, self.get_y(), 90)
        self._draw_company_block("Вантажоотримувач:", self.client, 110, self.get_y() - 25, 90)
        self.ln(10)

    def build(self, items: list[dict], filepath: str) -> str:
        self.add_page()  # header() викликається автоматично

        headers = ["№", "Найменування", "Од.", "К-ть", "Вага, кг", "Ціна", "Сума"]
        widths = [10, 70, 15, 15, 20, 30, 35]

        self._draw_table_header(headers, widths, self.get_y())

        total_qty = 0
        total_weight = 0.0
        subtotal = 0.0

        for i, item in enumerate(items, 1):
            qty = item.get("qty", 1)
            weight = item.get("weight_kg", 0) or 0
            total = item.get("total", 0)

            cells = [
                str(i),
                item.get("name", ""),
                item.get("unit", "шт"),
                str(qty),
                f"{weight:.2f}",
                f"{item.get('price', 0):,.2f}",
                f"{total:,.2f}",
            ]
            self._draw_table_row(cells, widths)
            total_qty += qty
            total_weight += weight
            subtotal += total

        # Підсумковий рядок
        self.set_font("DejaVu", "B", 9)
        self.cell(10, 6, "", border=1)
        self.cell(70, 6, "ВСЬОГО:", border=1, align="R")
        self.cell(15, 6, "", border=1)
        self.cell(15, 6, str(total_qty), border=1, align="C")
        self.cell(20, 6, f"{total_weight:.2f}", border=1, align="C")
        self.cell(30, 6, "", border=1)
        self.cell(35, 6, f"{subtotal:,.2f}", border=1, align="R")
        self.ln()

        self.ln(5)
        self._draw_totals(subtotal)

        self.ln(10)
        self._draw_signatures(self.get_y())

        self.output(filepath)
        return filepath
