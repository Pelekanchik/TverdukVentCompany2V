"""Add work scheduling, warehouse and purchase price history

Revision ID: 010
Revises: 009
Create Date: 2026-10-05 20:30:00

1. project_works: + work_date (дата монтажу/виконання), crew (бригада/виконавець)
2. warehouse_items / warehouse_moves — простий облік складу
3. purchase_prices — історія закупівельних цін для заявок на матеріали

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Планування робіт — додати колонки, якщо їх ще немає
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("project_works")]
    if "work_date" not in columns:
        op.add_column("project_works", sa.Column("work_date", sa.Date(), nullable=True))
    if "crew" not in columns:
        op.add_column("project_works", sa.Column("crew", sa.String(length=120), nullable=True))

    # 2. Склад
    op.create_table(
        "warehouse_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=30), server_default="шт", nullable=False),
        sa.Column("quantity", sa.Float(), server_default="0", nullable=False),
        sa.Column("min_quantity", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "warehouse_moves",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("warehouse_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("move_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("kind", sa.String(length=10), server_default="in", nullable=False),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.String(length=300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Історія закупівельних цін
    op.create_table(
        "purchase_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("supplier", sa.String(length=255), server_default="", nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_purchase_prices_name", "purchase_prices", ["item_name"])


def downgrade() -> None:
    op.drop_index("idx_purchase_prices_name", table_name="purchase_prices")
    op.drop_table("purchase_prices")
    op.drop_table("warehouse_moves")
    op.drop_table("warehouse_items")
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("project_works")]
    if "crew" in columns:
        op.drop_column("project_works", "crew")
    if "work_date" in columns:
        op.drop_column("project_works", "work_date")
