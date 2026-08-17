"""Initial migration — create all tables

Revision ID: f3015baf88f8
Revises: 
Create Date: 2026-08-17 19:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Імпортуємо на рівні модуля (не всередині функцій)
from ventilation_company.database.base import Base
from ventilation_company.database.db import engine

# Реєструємо моделі, щоб таблиці потрапили в Base.metadata
# noqa: F401 — імпорти потрібні для побічного ефекту (реєстрація таблиць)
from ventilation_company.database.models import project  # noqa: F401
from ventilation_company.database.models import product  # noqa: F401
from ventilation_company.database.models import calculation  # noqa: F401
from ventilation_company.database.models import employee  # noqa: F401
from ventilation_company.database.models import work_catalog  # noqa: F401
from ventilation_company.database.models import calc  # noqa: F401
from ventilation_company.database.models import unified  # noqa: F401
from ventilation_company.database.models import user  # noqa: F401
from ventilation_company.database.models import calc_template  # noqa: F401

# revision identifiers, used by Alembic.
revision = 'f3015baf88f8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Створити всі таблиці з поточних ORM-моделей."""
    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    """Видалити всі таблиці."""
    Base.metadata.drop_all(bind=engine)
