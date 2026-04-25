"""Add one-time collection operations tables.

Revision ID: 20260425_0002
Revises: 20260421_0001
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


revision = "20260425_0002"
down_revision = "20260421_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column("collection_locked", sa.Boolean(), nullable=True, server_default=sa.text("0")),
    )
    op.add_column("system_settings", sa.Column("collection_lock_reason", sa.Text(), nullable=True))
    op.add_column("system_settings", sa.Column("collection_locked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("employee_id", sa.String(length=20), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_employee_id"), "audit_logs", ["employee_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_status"), "audit_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_status"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_employee_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_column("system_settings", "collection_locked_at")
    op.drop_column("system_settings", "collection_lock_reason")
    op.drop_column("system_settings", "collection_locked")
