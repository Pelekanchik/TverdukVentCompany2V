"""Add client_id to projects

Revision ID: 006
Revises: 005
Create Date: 2026-09-24 23:30:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from ventilation_company.database.models.project import Project

    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns(Project.__tablename__)]
    if "client_id" not in columns:
        op.add_column(Project.__tablename__, sa.Column("client_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    pass
