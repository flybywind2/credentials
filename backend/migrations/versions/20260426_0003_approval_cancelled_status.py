"""Allow cancelled approval status.

Revision ID: 20260426_0003
Revises: 20260425_0002
Create Date: 2026-04-26
"""
from alembic import op


revision = "20260426_0003"
down_revision = "20260425_0002"
branch_labels = None
depends_on = None


REQUEST_STATUS_WITH_CANCELLED = "status in ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'CANCELLED')"
REQUEST_STATUS_LEGACY = "status in ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED')"
STEP_STATUS_WITH_CANCELLED = "status in ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')"
STEP_STATUS_LEGACY = "status in ('PENDING', 'APPROVED', 'REJECTED')"


def _recreate_mode() -> str:
    return "always" if op.get_bind().dialect.name == "sqlite" else "auto"


def _replace_check_constraint(table_name: str, name: str, expression: str) -> None:
    with op.batch_alter_table(table_name, recreate=_recreate_mode()) as batch_op:
        batch_op.drop_constraint(name, type_="check")
        batch_op.create_check_constraint(name, expression)


def upgrade() -> None:
    _replace_check_constraint(
        "approval_requests",
        "ck_approval_requests_status",
        REQUEST_STATUS_WITH_CANCELLED,
    )
    _replace_check_constraint(
        "approval_steps",
        "ck_approval_steps_status",
        STEP_STATUS_WITH_CANCELLED,
    )


def downgrade() -> None:
    op.execute("UPDATE approval_steps SET status='REJECTED' WHERE status='CANCELLED'")
    op.execute("UPDATE approval_requests SET status='REJECTED' WHERE status='CANCELLED'")
    _replace_check_constraint(
        "approval_steps",
        "ck_approval_steps_status",
        STEP_STATUS_LEGACY,
    )
    _replace_check_constraint(
        "approval_requests",
        "ck_approval_requests_status",
        REQUEST_STATUS_LEGACY,
    )
