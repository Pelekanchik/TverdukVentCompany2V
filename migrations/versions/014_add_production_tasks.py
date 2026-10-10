"""Add production_tasks table

Revision ID: 014
Revises: 013
Create Date: 2026-10-10 13:45:00

Черга виробництва (вкладка «Виробництво»): вироби з проєктів
з пріоритетами, статусами та плановими датами.

"""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("priority", sa.String(length=50), server_default="звичайний"),
        sa.Column("status", sa.String(length=50), server_default="в черзі"),
        sa.Column("planned_start", sa.DateTime(), nullable=True),
        sa.Column("planned_end", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.String(length=500), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_production_tasks_project_id", "production_tasks", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_production_tasks_project_id", table_name="production_tasks")
    op.drop_table("production_tasks")
