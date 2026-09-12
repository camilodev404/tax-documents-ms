"""create income tax brackets

Revision ID: 0001_create_income_tax_brackets
Revises:
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_create_income_tax_brackets"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "income_tax_brackets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_record_id", sa.Integer(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("income_min", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("income_max", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("tax_rate", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("source_document", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document",
            "source_record_id",
            name="uq_income_tax_brackets_source_document_record_id",
        ),
    )
    op.create_index(
        op.f("ix_income_tax_brackets_tax_year"),
        "income_tax_brackets",
        ["tax_year"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_income_tax_brackets_tax_year"), table_name="income_tax_brackets")
    op.drop_table("income_tax_brackets")
