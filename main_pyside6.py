"""VentCompany — PySide6 версія.

Запуск:
    python main_pyside6.py
"""

import sys
import os

# Додаємо корінь проєкту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ventilation_company.gui_pyside6.main_window import run_app

if __name__ == "__main__":
    run_app()
