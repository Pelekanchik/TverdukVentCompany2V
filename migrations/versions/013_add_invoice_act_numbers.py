"""Add invoice_number and act_number to projects

Revision ID: 013
Revises: 012
Create Date: 2026-10-08 19:05:00

projects: + invoice_number (VARCHAR(40), NULL) — рахунок на оплату,
  + act_number (VARCHAR(40), NULL) — акт виконаних робіт.
Автонумерація Р-YYYYMMDD-NNN і АК-YYYYMMDD-NNN; зберігаються в проєкті,
щоб повторне формування документа не змінювало номер.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

_NEW_COLUMNS = ("invoice_number", "act_number")


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("projects")]
    for name in _NEW_COLUMNS:
        if name not in columns:
            op.add_column(
                "projects",
                sa.Column(name, sa.String(length=40), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("projects")]
    for name in _NEW_COLUMNS:
        if name in columns:
            op.drop_column("projects", name)
