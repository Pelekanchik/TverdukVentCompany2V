"""Add contract_number to projects

Revision ID: 012
Revises: 011
Create Date: 2026-10-08 17:10:00

projects: + contract_number (VARCHAR(40), NULL) — номер договору
з автонумерацією ДГ-YYYYMMDD-NNN. Зберігається в проєкті, щоб повторне
формування договору не змінювало номер.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("projects")]
    if "contract_number" not in columns:
        op.add_column(
            "projects",
            sa.Column("contract_number", sa.String(length=40), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("projects")]
    if "contract_number" in columns:
        op.drop_column("projects", "contract_number")
