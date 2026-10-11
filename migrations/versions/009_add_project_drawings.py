"""Add project_drawings table

Revision ID: 009
Revises: 008
Create Date: 2026-09-29 12:00:00

Креслення проєкту — посилання на зовнішні файли (DWG/DXF/PDF,
моделі Revit/FreeCAD) з картки проєкту.

"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_drawings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("drawing_type", sa.String(length=50), nullable=False, server_default="креслення"),
        sa.Column("notes", sa.String(length=500), server_default=""),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("project_drawings")
