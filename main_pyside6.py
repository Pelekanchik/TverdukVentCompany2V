"""VentCompany — PySide6 версія.

Запуск:
    python main_pyside6.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_migrations() -> None:
    """Застосувати міграції Alembic. Без create_all fallback."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("[DB] Помилка міграцій Alembic:")
        print(result.stdout or "")
        print(result.stderr or "")
        raise SystemExit(1)
    print("[DB] Міграції Alembic застосовано")


def main() -> None:
    run_migrations()
    from ventilation_company.gui_pyside6.main_window import run_app

    run_app()


if __name__ == "__main__":
    main()
