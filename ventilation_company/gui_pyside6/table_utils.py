"""Єдине налаштування таблиць VentCompany.

Усі таблиці програми (QTableView/QTableWidget) проходять через setup_table():
однакова висота рядків (щоб редактори комірок поміщалися й текст не обрізався),
смугастий фон, прихований вертикальний заголовок, єдина поведінка вибору.
"""

from PySide6.QtWidgets import QAbstractItemView, QTableView

# Стандартна висота рядка: з запасом під компактний редактор комірки (див. theme.py)
DEFAULT_ROW_HEIGHT = 32


def setup_table(
    table: QTableView,
    *,
    select_rows: bool = False,
    single_selection: bool = False,
    extended_selection: bool = False,
    sorting: bool = False,
    read_only: bool = False,
    stretch_last: bool = True,
    alternating: bool = True,
    row_height: int = DEFAULT_ROW_HEIGHT,
) -> None:
    """Застосувати єдиний стиль і поведінку до таблиці.

    Параметри:
        select_rows: вибирати цілі рядки замість окремих комірок.
        single_selection: лише один рядок/комірка за раз.
        extended_selection: дозволити вибір кількох рядків (Ctrl/Shift).
        sorting: ввімкнути сортування кліком по заголовку.
        read_only: заборонити редагування комірок (лише перегляд).
        stretch_last: остання колонка розтягується на вільне місце.
        alternating: смугастий фон рядків.
        row_height: стандартна висота рядка в пікселях.
    """
    if alternating:
        table.setAlternatingRowColors(True)
    vh = table.verticalHeader()
    vh.setVisible(False)
    vh.setDefaultSectionSize(row_height)
    vh.setMinimumSectionSize(row_height)
    if stretch_last:
        table.horizontalHeader().setStretchLastSection(True)
    if select_rows:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    if single_selection:
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    if extended_selection:
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    if sorting:
        table.setSortingEnabled(True)
    if read_only:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
