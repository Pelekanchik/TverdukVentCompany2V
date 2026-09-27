# Alter payment client_id nullable
# Revision ID: 008
# Revises: 007

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from ventilation_company.database.models.unified import Payment

    bind = op.get_bind()
    columns = {c["name"]: c for c in inspect(bind).get_columns(Payment.__tablename__)}
    if "client_id" in columns and columns["client_id"].get("nullable") is False:
        op.alter_column(
            Payment.__tablename__, "client_id", existing_type=sa.Integer(), nullable=True
        )


def downgrade() -> None:
    pass
