"""Runtime bootstrap for source and frozen builds."""

from __future__ import annotations

from ventilation_company.paths import APP_ROOT, DATA_DIR, DOCUMENTS_DIR, LOGS_DIR

BACKUP_DIR = APP_ROOT / "backups"


def ensure_runtime_dirs() -> None:
    """Create runtime directories on first start."""
    for directory in (APP_ROOT, DATA_DIR, LOGS_DIR, DOCUMENTS_DIR, BACKUP_DIR):
        directory.mkdir(parents=True, exist_ok=True)
