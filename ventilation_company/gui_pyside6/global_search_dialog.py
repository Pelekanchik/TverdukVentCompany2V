"""Діалог глобального пошуку (Ctrl+G).

Шукає по проєктах, виробах, роботах, кресленнях і клієнтах.
Enter / подвійний клік — відкрити картку проєкту результату.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from ventilation_company.services.global_search import search_all

_KIND_ICONS = {
    "projects": "📁",
    "products": "🔧",
    "works": "🔨",
    "drawings": "📐",
    "clients": "👤",
}


class GlobalSearchDialog(QDialog):
    """Миттєвий пошук по всій програмі."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пошук по програмі")
        self.setMinimumSize(560, 440)
        self._results: list[dict] = []

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("🔍"))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("назва проєкту, виробу, роботи, креслення, клієнта…")
        self.edit.textChanged.connect(self._run_search)
        top.addWidget(self.edit, 1)
        layout.addLayout(top)

        self.list = QListWidget()
        self.list.itemActivated.connect(self._on_activated)
        layout.addWidget(self.list, 1)

        self.lbl_hint = QLabel(
            "Введіть текст — результати з'являться одразу. " "Enter — відкрити проєкт."
        )
        layout.addWidget(self.lbl_hint)

        self.edit.setFocus()

    # ── Пошук ──

    def _run_search(self):
        query = self.edit.text()
        self.list.clear()
        self._results = []
        if len(query.strip()) < 2:
            return
        try:
            self._results = search_all(query)
        except Exception:  # noqa: BLE001 — пошук не має руйнувати діалог
            self._results = []
        for r in self._results:
            icon = _KIND_ICONS.get(r["kind"], "•")
            item = QListWidgetItem(f"{icon}  {r['title']}\n      {r['subtitle']}")
            self.list.addItem(item)

    # ── Дії ──

    def _on_activated(self, _item=None):
        row = self.list.currentRow()
        if not (0 <= row < len(self._results)):
            return
        result = self._results[row]
        project_id = result.get("project_id")
        if project_id:
            self.accept()
            self._open_project(project_id)
        # Для клієнтів (project_id=None) — лише перегляд результату

    def _open_project(self, project_id):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        dlg = ProjectCardDialog(project_id, parent=self.parent())
        dlg.exec()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.list.count() > 0:
            if self.list.currentRow() < 0:
                self.list.setCurrentRow(0)
            self._on_activated()
            return
        super().keyPressEvent(event)
