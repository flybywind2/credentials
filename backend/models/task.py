from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class TaskEntry(Base):
    __tablename__ = "task_entries"
    __table_args__ = (
        CheckConstraint(
            "status in ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')",
            name="ck_task_entries_status",
        ),
        CheckConstraint(
            "conf_owner_user is null or conf_owner_user in ('OWNER', 'USER')",
            name="ck_task_entries_conf_owner_user",
        ),
        CheckConstraint(
            "ntech_owner_user is null or ntech_owner_user in ('OWNER', 'USER')",
            name="ck_task_entries_ntech_owner_user",
        ),
        CheckConstraint(
            "comp_owner_user is null or comp_owner_user in ('OWNER', 'USER')",
            name="ck_task_entries_comp_owner_user",
        ),
        CheckConstraint(
            "share_scope is null or share_scope in ('DIVISION_BU', 'BUSINESS_UNIT', 'ORG_UNIT')",
            name="ck_task_entries_share_scope",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    sub_part: Mapped[str | None] = mapped_column(String(100), nullable=True)
    major_task: Mapped[str] = mapped_column(String(200), nullable=False)
    detail_task: Mapped[str] = mapped_column(String(500), nullable=False)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    conf_data_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    conf_owner_user: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_national_tech: Mapped[bool] = mapped_column(Boolean, default=False)
    ntech_data_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    ntech_owner_user: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_compliance: Mapped[bool] = mapped_column(Boolean, default=False)
    comp_data_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    comp_owner_user: Mapped[str | None] = mapped_column(String(20), nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    related_menu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    share_scope: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TaskQuestionCheck(Base):
    __tablename__ = "task_question_checks"
    __table_args__ = (
        CheckConstraint(
            "question_type in ('CONFIDENTIAL', 'NATIONAL_TECH')",
            name="ck_task_question_checks_question_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_entry_id: Mapped[int] = mapped_column(
        ForeignKey("task_entries.id"), nullable=False
    )
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_options: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
