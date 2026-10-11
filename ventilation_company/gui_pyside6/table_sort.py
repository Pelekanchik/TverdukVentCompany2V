"""Числове сортування для таблиць на QStandardItemModel.

Проблема: QStandardItemModel сортує за текстом (DisplayRole), тому
«₴ 1 000» вважається меншим за «₴ 200». Рішення: NumericSortModel
сортує колонки за числовим значенням Qt.UserRole, яке встановлює
numeric_item() — текстове відображення при цьому не змінюється.

Використання:
    self.model = NumericSortModel()
    ...
    row = [numeric_item(price, f"{price:,.2f}"), QStandardItem("назва")]
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel


class NumericSortModel(QStandardItemModel):
    """QStandardItemModel, у якій колонки з Qt.UserRole сортуються як числа."""

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self._column_has_numeric(column):
            super().sort(column, order)
            return
        # Числове сортування: забираємо рядки з кінця, сортуємо, повертаємо
        rows = []
        for r in range(self.rowCount() - 1, -1, -1):
            items = self.takeRow(r)
            num = items[column].data(Qt.ItemDataRole.UserRole) if column < len(items) else None
            rows.append((num, items))
        rows.sort(
            key=lambda t: (t[0] is None, float(t[0]) if t[0] is not None else 0.0),
            reverse=(order == Qt.SortOrder.DescendingOrder),
        )
        for _num, items in rows:
            self.appendRow(items)

    def _column_has_numeric(self, column: int) -> bool:
        for r in range(self.rowCount()):
            item = self.item(r, column)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) is not None:
                return True
        return False


def numeric_item(value, text: str) -> QStandardItem:
    """Елемент таблиці: виглядає як text, сортується як число value."""
    item = QStandardItem(text)
    try:
        item.setData(float(value), Qt.ItemDataRole.UserRole)
    except (TypeError, ValueError):
        pass
    return item
