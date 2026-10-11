"""Add reserved column to warehouse_items

Revision ID: 015
Revises: 014
Create Date: 2026-10-10 14:40:00

Резервування матеріалів під заявки (склад у виробництві):
reserved — кількість, зарезервована під виробництво; доступно = quantity - reserved.

"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "warehouse_items",
        sa.Column("reserved", sa.Float(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("warehouse_items", "reserved")
