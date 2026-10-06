"""Add is_done flag to project works

Revision ID: 011
Revises: 010
Create Date: 2026-10-06 15:20:00

project_works: + is_done (BOOLEAN, NOT NULL, default false) —
статус виконання роботи. Виконані роботи не потрапляють у активний
план монтажів, але лишаються в історії та звітах.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("project_works")]
    if "is_done" not in columns:
        op.add_column(
            "project_works",
            sa.Column(
                "is_done",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("project_works")]
    if "is_done" in columns:
        op.drop_column("project_works", "is_done")
