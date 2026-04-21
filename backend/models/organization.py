from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "org_type in ('NORMAL', 'TEAM_DIRECT', 'DIV_DIRECT')",
            name="ck_organizations_org_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    division_name: Mapped[str] = mapped_column(String(100), nullable=False)
    division_head_name: Mapped[str] = mapped_column(String(50), nullable=False)
    division_head_id: Mapped[str] = mapped_column(String(20), nullable=False)
    team_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team_head_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    team_head_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_head_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    group_head_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    part_head_name: Mapped[str] = mapped_column(String(50), nullable=False)
    part_head_id: Mapped[str] = mapped_column(String(20), nullable=False)
    org_type: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
