# Add project_id to payments
# Revision ID: 007
# Revises: 006

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from ventilation_company.database.models.unified import Payment

    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns(Payment.__tablename__)]
    if "project_id" not in columns:
        op.add_column(Payment.__tablename__, sa.Column("project_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    pass
