"""РљРѕРЅС‚РµРєСЃС‚ Р±Р°Р·Рё РґР°РЅРёС… РґР»СЏ GUI."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.repositories.calc_repo import CalculationRepository
from ventilation_company.database.repositories.material_repo import (
    MaterialRepository as MaterialRepository,
)
from ventilation_company.database.repositories.overhead_repo import (
    OverheadRepository as OverheadRepository,
)
from ventilation_company.database.repositories.product_repo import (
    ProductRepository as ProductRepository,
)
from ventilation_company.database.repositories.settings_repo import (
    SettingsRepository as SettingsRepository,
)


class DatabaseContext:
    """Р„РґРёРЅРёР№ РєРѕРЅС‚РµРєСЃС‚ Р‘Р” РґР»СЏ GUI. РЎС‚РІРѕСЂСЋС” СЃРµСЃС–СЋ РїСЂРё С–РЅС–С†С–Р°Р»С–Р·Р°С†С–С—."""

    def __init__(self):
        self.session = SessionLocal()
        self.products = ProductRepository(self.session)
        self.calculations = CalculationRepository(self.session)
        self.materials = MaterialRepository(self.session)
        self.overheads = OverheadRepository(self.session)
        self.settings = SettingsRepository(self.session)

    def close(self) -> None:
        self.session.close()

    def commit(self) -> None:
        self.session.commit()


@contextmanager
def db_context() -> Generator[DatabaseContext, None, None]:
    """Context manager РґР»СЏ Р±РµР·РїРµС‡РЅРѕС— СЂРѕР±РѕС‚Рё Р· Р‘Р”."""
    ctx = DatabaseContext()
    try:
        yield ctx
    finally:
        ctx.close()
