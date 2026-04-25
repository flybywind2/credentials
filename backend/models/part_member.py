from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PartMember(Base):
    __tablename__ = "part_members"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "part_name",
            "knox_id",
            name="uq_part_members_org_part_knox",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    knox_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TaskAssignee(Base):
    __tablename__ = "task_assignees"
    __table_args__ = (
        UniqueConstraint("task_entry_id", "knox_id", name="uq_task_assignees_task_knox"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_entry_id: Mapped[int] = mapped_column(
        ForeignKey("task_entries.id"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    knox_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
