from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(
            "status in ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_approval_requests_status",
        ),
        CheckConstraint("current_step >= 1", name="ck_approval_requests_current_step"),
        CheckConstraint("total_steps >= 1", name="ck_approval_requests_total_steps"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    __table_args__ = (
        CheckConstraint(
            "status in ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_approval_steps_status",
        ),
        CheckConstraint("step_order >= 1", name="ck_approval_steps_step_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    approval_request_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_employee_id: Mapped[str] = mapped_column(String(20), nullable=False)
    approver_name: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ApprovalTaskReview(Base):
    __tablename__ = "approval_task_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision in ('APPROVED', 'REJECTED')",
            name="ck_approval_task_reviews_decision",
        ),
        UniqueConstraint(
            "approval_step_id",
            "task_entry_id",
            name="uq_approval_task_reviews_step_task",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    approval_request_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=False
    )
    approval_step_id: Mapped[int] = mapped_column(
        ForeignKey("approval_steps.id"), nullable=False
    )
    task_entry_id: Mapped[int] = mapped_column(
        ForeignKey("task_entries.id"), nullable=False
    )
    reviewer_employee_id: Mapped[str] = mapped_column(String(20), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
