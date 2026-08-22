"""Рахунок-фактура (з ПДВ)."""

from datetime import datetime

from ventilation_company.documents.base import BaseDocument
from ventilation_company.documents.company_info import CompanyInfo


class Invoice(BaseDocument):
    """Рахунок-фактура на оплату (з ПДВ)."""

    def __init__(self, company: CompanyInfo, client: CompanyInfo, invoice_number: str = ""):
        super().__init__(company, client, title="РАХУНОК-ФАКТУРА")
        self.doc_number = invoice_number or f"РФ-{datetime.now().strftime('%Y%m%d-%H%M')}"

    def header(self):
        """Заголовок рахунка-фактури."""
        # Логотип / назва
        self.set_font("DejaVu", "B", 14)
        self.cell(0, 10, self.doc_title, ln=True, align="C")

        self.set_font("DejaVu", "", 10)
        self.cell(0, 6, f"№ {self.doc_number} від {self.doc_date}", ln=True, align="C")
        self.ln(4)

        # Реквізити
        self._draw_company_block(
            "Постачальник:", self.company, x=10, y=self.get_y(), w=90
        )
        self._draw_company_block(
            "Платник:", self.client, x=110, y=self.get_y() - 25, w=90
        )
        self.ln(10)

    def build(self, items: list[dict], filepath: str) -> str:
        """Побудувати рахунок-фактуру.

        items: [{name, unit, qty, price, total}]
        """
        self.add_page()  # header() викликається автоматично

        # Таблиця
        headers = ["№", "Найменування", "Од.", "К-ть", "Ціна без ПДВ", "Сума без ПДВ"]
        widths = [10, 80, 15, 20, 35, 35]

        self._draw_table_header(headers, widths, self.get_y())

        subtotal = 0.0
        for i, item in enumerate(items, 1):
            cells = [
                str(i),
                item.get("name", ""),
                item.get("unit", "шт"),
                str(item.get("qty", 1)),
                f"{item.get('price', 0):,.2f}",
                f"{item.get('total', 0):,.2f}",
            ]
            self._draw_table_row(cells, widths)
            subtotal += float(item.get("total", 0))

        self.ln(5)
        self._draw_totals(subtotal, vat_rate=20.0 if self.company.vat_payer else 0.0)

        self.ln(10)
        self._draw_signatures(self.get_y())

        # Примітка
        self.set_y(-40)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 4, 
            f"Примітка: Рахунок дійсний до сплати протягом 5 банківських днів. "
            f"Після оплати надішліть копію платіжного доручення на {self.company.email}"
        )

        self.output(filepath)
        return filepath
