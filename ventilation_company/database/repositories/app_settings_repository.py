"""App settings repository extracted from ProgramSettingsTab."""

from __future__ import annotations

from urllib.parse import urlparse

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.calc import CalcSetting


class AppSettingsRepository:
    """CRUD для програмних налаштувань через таблицю calc_settings."""

    _CACHE: dict[str, str] = {}

    def __init__(self):
        self._session_factory = SessionLocal

    def _session(self):
        return self._session_factory()

    def get(self, key: str, default: str = "") -> str:
        if key in self._CACHE:
            return self._CACHE[key]
        session = self._session()
        try:
            row = session.query(CalcSetting).filter(CalcSetting.key == key).first()
            val = row.value if row else default
            self._CACHE[key] = val
            return val
        finally:
            session.close()

    def set(self, key: str, value: str) -> None:
        session = self._session()
        try:
            row = session.query(CalcSetting).filter(CalcSetting.key == key).first()
            if row:
                row.value = value
            else:
                session.add(CalcSetting(key=key, value=value))
            session.commit()
            self._CACHE[key] = value
        finally:
            session.close()

    def clear_cache(self):
        self._CACHE.clear()


# ═══════════════════════════════════════════════════════════════════
# Хелпери
# ═══════════════════════════════════════════════════════════════════
ROLE_LABELS = {
    "admin": "Адміністратор",
    "manager": "Менеджер",
    "engineer": "Інженер",
    "master": "Майстер",
    "accountant": "Бухгалтер",
    "viewer": "Перегляд",
    "director": "Директор",
    "monter": "Монтажник",
}


def get_role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def _mask_url(url: str) -> str:
    """Замаскувати пароль у DATABASE_URL."""
    if "://" not in url:
        return url
    try:
        parsed = urlparse(url)
        if parsed.password:
            return url.replace(f":{parsed.password}@", ":***@")
    except Exception:
        pass
    return url


# ═══════════════════════════════════════════════════════════════════
# Головний клас
# ═══════════════════════════════════════════════════════════════════
