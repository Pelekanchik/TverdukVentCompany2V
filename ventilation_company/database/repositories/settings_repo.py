"""ORM-репозиторій для роботи з налаштуваннями."""

from sqlalchemy.orm import Session

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.calc import CalcSetting


class SettingsRepository:
    """CRUD для calc_settings через ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[CalcSetting]:
        return self.db.query(CalcSetting).all()

    def get_value(self, key: str, default: str | None = None) -> str:
        setting = self.db.query(CalcSetting).filter(CalcSetting.key == key).first()
        return setting.value if setting else default

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get_value(key)
        return int(val) if val is not None else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        val = self.get_value(key)
        return float(val) if val is not None else default

    def set_value(self, key: str, value: str) -> CalcSetting:
        setting = self.db.query(CalcSetting).filter(CalcSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = CalcSetting(key=key, value=value)
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def delete(self, key: str) -> bool:
        setting = self.db.query(CalcSetting).filter(CalcSetting.key == key).first()
        if not setting:
            return False
        self.db.delete(setting)
        self.db.commit()
        return True

    def get(self, key: str, default: str | None = None) -> str | None:
        """Alias for get_value."""
        return self.get_value(key, default)

        # Зворотна сумісність — аліаси для старих методів

    set = set_value


# Зворотна сумісність
SettingsRepo = SettingsRepository


SettingsRepo = SettingsRepository(SessionLocal())
