"""Базовий клас для вкладок із комбобоксом вибору проєкту.

Єдиний правильний патерн обробки зовнішньої зміни активного проєкту:
якщо проєкту немає у combo_project — список застарів (проєкт щойно
створено, продубльовано чи видалено), і його треба перезавантажити.

Без цього патерну новий проєкт не з'являвся у вкладках до перезапуску
програми (баг v2.8.0 у вкладці «Вироби»).

Підкласи мають:
  • атрибут combo_project (QComboBox із project_id у userData);
  • _reload_project_list() — перезавантаження списку (метод сам
    повинен обрати активний проєкт, якщо він відомий main_window);
  • опційно _after_project_changed(project_id) — оновлення таблиці
    даних після зміни вибору.
"""

from PySide6.QtWidgets import QWidget


class ProjectAwareTab(QWidget):
    """Вкладка з вибором проєкту: безпечна обробка on_project_changed."""

    #: combo_project має бути створений у _build_ui() підкласу.
    combo_project = None

    def _reload_project_list(self):
        """Перезавантажити список проєктів у combo_project."""
        raise NotImplementedError

    def _after_project_changed(self, project_id: int | None):
        """Хук: оновити дані вкладки після зміни проєкту (за замовчуванням — нічого)."""

    def on_project_changed(self, project_id: int | None):
        """Зовнішня зміна активного проєкту (викликає MainWindow)."""
        if project_id:
            idx = self.combo_project.findData(project_id)
            if idx < 0:
                # Проєкту немає у combo — список застарів. Перезавантажуємо
                # і шукаємо ще раз (_reload_project_list сам обере активний).
                self._reload_project_list()
                idx = self.combo_project.findData(project_id)
            if idx >= 0:
                self.combo_project.blockSignals(True)
                self.combo_project.setCurrentIndex(idx)
                self.combo_project.blockSignals(False)
        else:
            self.combo_project.blockSignals(True)
            self.combo_project.setCurrentIndex(-1)
            self.combo_project.blockSignals(False)
        self._after_project_changed(project_id)
