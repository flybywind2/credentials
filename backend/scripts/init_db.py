import argparse

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    ApprovalRequest,
    ApprovalStep,
    ConfidentialQuestion,
    NationalTechQuestion,
    Organization,
    SystemSetting,
    TaskEntry,
    User,
)
from backend.seed import (
    CURRENT_USER,
    ORGANIZATIONS,
    PENDING_APPROVALS,
    QUESTIONS,
    TASKS,
)


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def initialize_database(database_url: str = "sqlite:///./dev.db", reset: bool = False) -> None:
    engine = create_engine(database_url, connect_args=_sqlite_connect_args(database_url))
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _ensure_incremental_columns(engine)

    session = sessionmaker(bind=engine)()
    try:
        if session.query(Organization).first():
            return

        organizations = []
        for item in ORGANIZATIONS:
            org = Organization(**item)
            session.add(org)
            organizations.append(org)
        session.flush()

        user = User(
            employee_id=CURRENT_USER["employee_id"],
            name=CURRENT_USER["name"],
            role=CURRENT_USER["role"],
            organization_id=organizations[0].id,
        )
        session.add(user)
        session.flush()

        for item in QUESTIONS["confidential"]:
            session.add(ConfidentialQuestion(**item, is_active=True))
        for item in QUESTIONS["national_tech"]:
            session.add(NationalTechQuestion(**item, is_active=True))

        for item in TASKS:
            task_data = {
                key: value
                for key, value in item.items()
                if key not in {"id", "organization_id"}
            }
            session.add(
                TaskEntry(
                    organization_id=organizations[0].id,
                    created_by=user.id,
                    **task_data,
                )
            )

        for item in PENDING_APPROVALS:
            approval = ApprovalRequest(
                organization_id=organizations[0].id,
                requested_by=user.id,
                status=item["status"],
                current_step=item["current_step"],
                total_steps=item["total_steps"],
            )
            session.add(approval)
            session.flush()
            approver_ids = ["group001", "team001", "div001"]
            approver_names = ["박그룹장", "이팀장", "김실장"]
            approver_roles = ["그룹장", "팀장", "실장"]
            for index, approver_id in enumerate(approver_ids, start=1):
                session.add(
                    ApprovalStep(
                        approval_request_id=approval.id,
                        step_order=index,
                        approver_employee_id=approver_id,
                        approver_name=approver_names[index - 1],
                        approver_role=approver_roles[index - 1],
                        status="PENDING",
                    )
                )

        session.add(SystemSetting())
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_incremental_columns(engine) -> None:
    inspector = inspect(engine)
    if "system_settings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("system_settings")}
    if "description" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE system_settings ADD COLUMN description TEXT"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the local development DB.")
    parser.add_argument("--database-url", default="sqlite:///./dev.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    initialize_database(database_url=args.database_url, reset=args.reset)


if __name__ == "__main__":
    main()
