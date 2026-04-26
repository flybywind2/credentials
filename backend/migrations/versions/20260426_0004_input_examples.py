"""Add input example data setting.

Revision ID: 20260426_0004
Revises: 20260426_0003
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa


revision = "20260426_0004"
down_revision = "20260426_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("system_settings", sa.Column("input_examples_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("system_settings", "input_examples_json")
