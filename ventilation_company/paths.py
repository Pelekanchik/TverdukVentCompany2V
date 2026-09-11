"""Runtime paths that work both in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def _detect_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


APP_ROOT = _detect_app_root()
DATA_DIR = APP_ROOT / "data"
LOGS_DIR = APP_ROOT / "logs"
DOCUMENTS_DIR = APP_ROOT / "documents"
