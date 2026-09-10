"""VentCompany — PySide6 версія.

Запуск:
    python main_pyside6.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
MIGRATIONS_DONE_ENV = "VENTCOMPANY_MIGRATIONS_DONE"
LAUNCH_GUI = PROJECT_ROOT / "launch_gui.py"


def run_migrations() -> None:
    """Застосувати міграції Alembic перед стартом GUI."""
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
    if os.environ.get(MIGRATIONS_DONE_ENV) != "1":
        run_migrations()
        os.environ[MIGRATIONS_DONE_ENV] = "1"
        os.execv(sys.executable, [sys.executable, str(LAUNCH_GUI)])

    import launch_gui

    launch_gui.main()


if __name__ == "__main__":
    main()
