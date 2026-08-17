"""ORM-модель для шаблонів розрахунків (calc_templates).

Раніше ця таблиця створювалась через raw sqlite3 у template_repo.py,
але не була зареєстрована в ORM — тому Base.metadata.create_all() її пропускав.
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class CalcTemplate(Base):
    """Шаблони розрахунків (зворотна сумісність з template_repo)."""
    __tablename__ = "calc_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_data: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=True
    )
