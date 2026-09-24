"""Add direction to project expenses

Revision ID: 005
Revises: 004
Create Date: 2026-09-24 20:20:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from ventilation_company.database.models.project import ProjectExpense

    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns(ProjectExpense.__tablename__)]
    if "direction" not in columns:
        op.add_column(
            ProjectExpense.__tablename__, sa.Column("direction", sa.String(), nullable=True)
        )


def downgrade() -> None:
    pass
