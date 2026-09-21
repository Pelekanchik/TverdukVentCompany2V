"""Ensure CRM tables exist

Revision ID: 004
Revises: 003
Create Date: 2026-09-21 18:40:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def _create_table_if_missing(table) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table.name not in inspector.get_table_names():
        table.create(bind, checkfirst=True)


def upgrade() -> None:
    from ventilation_company.database.models.unified import (
        Client,
        ClientProject,
        Interaction,
        Payment,
        WarrantyReminder,
    )

    _create_table_if_missing(Client.__table__)
    _create_table_if_missing(ClientProject.__table__)
    _create_table_if_missing(Interaction.__table__)
    _create_table_if_missing(Payment.__table__)
    _create_table_if_missing(WarrantyReminder.__table__)

    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("clients")]
    if "status" not in columns:
        op.add_column("clients", sa.Column("status", sa.String(), nullable=True))


def downgrade() -> None:
    # Intentionally keep tables/column to avoid data loss.
    pass
