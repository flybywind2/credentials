import argparse

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalTaskReview,
    AuditLog,
    ConfidentialQuestion,
    NationalTechQuestion,
    Organization,
    PartMember,
    SystemSetting,
    TaskAssignee,
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

APPROVAL_REQUEST_STATUS_CHECK = "status in ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'CANCELLED')"
APPROVAL_STEP_STATUS_CHECK = "status in ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')"
TASK_ENTRY_STATUS_VALUES = ("UPLOADED", "DRAFT", "SUBMITTED", "APPROVED", "REJECTED")
TASK_ENTRY_STATUS_CHECK = "status in ('UPLOADED', 'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')"


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
    _ensure_uploaded_status_constraint(engine)
    _ensure_approval_cancelled_status_constraint(engine)

    session = sessionmaker(bind=engine)()
    try:
        if session.query(Organization).first():
            _normalize_existing_organizations(session)
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


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _org_type_from_hierarchy(team_name: str | None, group_name: str | None) -> str:
    if not team_name and not group_name:
        return "DIV_DIRECT"
    if not group_name:
        return "TEAM_DIRECT"
    return "NORMAL"


def _normalize_existing_organizations(session) -> None:
    optional_fields = (
        "team_name",
        "team_head_name",
        "team_head_id",
        "group_name",
        "group_head_name",
        "group_head_id",
    )
    required_fields = (
        "division_name",
        "division_head_name",
        "division_head_id",
        "part_name",
        "part_head_name",
        "part_head_id",
    )
    changed = False

    for org in session.query(Organization).all():
        for field in optional_fields:
            value = getattr(org, field)
            cleaned = _clean_optional_text(value)
            if cleaned != value:
                setattr(org, field, cleaned)
                changed = True
        for field in required_fields:
            value = getattr(org, field)
            if isinstance(value, str) and value.strip() != value:
                setattr(org, field, value.strip())
                changed = True
        org_type = _org_type_from_hierarchy(org.team_name, org.group_name)
        if org.org_type != org_type:
            org.org_type = org_type
            changed = True

    if changed:
        session.commit()


def _ensure_incremental_columns(engine) -> None:
    inspector = inspect(engine)
    if "system_settings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("system_settings")}
    with engine.begin() as connection:
        if "description" not in columns:
            connection.execute(text("ALTER TABLE system_settings ADD COLUMN description TEXT"))
        if "input_examples_json" not in columns:
            connection.execute(text("ALTER TABLE system_settings ADD COLUMN input_examples_json TEXT"))
        if "collection_locked" not in columns:
            connection.execute(text("ALTER TABLE system_settings ADD COLUMN collection_locked BOOLEAN DEFAULT 0"))
        if "collection_lock_reason" not in columns:
            connection.execute(text("ALTER TABLE system_settings ADD COLUMN collection_lock_reason TEXT"))
        if "collection_locked_at" not in columns:
            connection.execute(text("ALTER TABLE system_settings ADD COLUMN collection_locked_at DATETIME"))


def _ensure_uploaded_status_constraint(engine) -> None:
    if engine.dialect.name in {"mysql", "mariadb"}:
        inspector = inspect(engine)
        if "task_entries" not in inspector.get_table_names():
            return
        with engine.begin() as connection:
            _ensure_mysql_check_constraint(
                connection,
                "task_entries",
                "ck_task_entries_status",
                TASK_ENTRY_STATUS_CHECK,
                required_values=TASK_ENTRY_STATUS_VALUES,
            )
        return
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "task_entries" not in inspector.get_table_names():
        return
    with engine.begin() as connection:
        create_sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='task_entries'")
        ).scalar_one_or_none()
        if not create_sql or "UPLOADED" in create_sql:
            return

        old_table = "task_entries_old_status_migration"
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(text(f"ALTER TABLE task_entries RENAME TO {old_table}"))
        for index_name in connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=:table_name AND sql IS NOT NULL"),
            {"table_name": old_table},
        ).scalars():
            connection.execute(text(f"DROP INDEX {index_name}"))
        TaskEntry.__table__.create(bind=connection)
        old_columns = {
            row[1]
            for row in connection.execute(text(f"PRAGMA table_info({old_table})")).all()
        }
        new_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(task_entries)")).all()
        }
        shared_columns = [
            column.name
            for column in TaskEntry.__table__.columns
            if column.name in old_columns and column.name in new_columns
        ]
        column_list = ", ".join(shared_columns)
        connection.execute(
            text(f"INSERT INTO task_entries ({column_list}) SELECT {column_list} FROM {old_table}")
        )
        connection.execute(text(f"DROP TABLE {old_table}"))
        connection.execute(text("PRAGMA foreign_keys=ON"))


def _copy_shared_columns(connection, table, old_table_name: str) -> None:
    old_columns = {
        row[1]
        for row in connection.execute(text(f"PRAGMA table_info({old_table_name})")).all()
    }
    new_columns = {
        row[1]
        for row in connection.execute(text(f"PRAGMA table_info({table.name})")).all()
    }
    shared_columns = [
        column.name
        for column in table.columns
        if column.name in old_columns and column.name in new_columns
    ]
    if not shared_columns:
        return
    column_list = ", ".join(shared_columns)
    connection.execute(
        text(f"INSERT INTO {table.name} ({column_list}) SELECT {column_list} FROM {old_table_name}")
    )


def _drop_sqlite_indexes(connection, table_name: str) -> None:
    for index_name in connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=:table_name AND sql IS NOT NULL"),
        {"table_name": table_name},
    ).scalars():
        connection.execute(text(f"DROP INDEX {index_name}"))


def _quote_mysql_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def _mysql_drop_check_sql(table_name: str, constraint_name: str, is_mariadb: bool = False) -> str:
    drop_keyword = "DROP CONSTRAINT" if is_mariadb else "DROP CHECK"
    return (
        f"ALTER TABLE {_quote_mysql_identifier(table_name)} "
        f"{drop_keyword} {_quote_mysql_identifier(constraint_name)}"
    )


def _mysql_add_check_sql(table_name: str, constraint_name: str, expression: str) -> str:
    return (
        f"ALTER TABLE {_quote_mysql_identifier(table_name)} "
        f"ADD CONSTRAINT {_quote_mysql_identifier(constraint_name)} CHECK ({expression})"
    )


def _mysql_check_clause(connection, table_name: str, constraint_name: str) -> str | None:
    return connection.execute(
        text(
            """
            SELECT cc.check_clause
            FROM information_schema.check_constraints cc
            JOIN information_schema.table_constraints tc
              ON cc.constraint_schema = tc.constraint_schema
             AND cc.constraint_name = tc.constraint_name
            WHERE tc.table_schema = DATABASE()
              AND tc.table_name = :table_name
              AND tc.constraint_name = :constraint_name
              AND tc.constraint_type = 'CHECK'
            """
        ),
        {"table_name": table_name, "constraint_name": constraint_name},
    ).scalar_one_or_none()


def _has_required_check_values(current_clause: str, required_values: tuple[str, ...]) -> bool:
    clause = current_clause.upper()
    return all(value.upper() in clause for value in required_values)


def _ensure_mysql_check_constraint(
    connection,
    table_name: str,
    constraint_name: str,
    expression: str,
    *,
    required_values: tuple[str, ...],
) -> None:
    current_clause = _mysql_check_clause(connection, table_name, constraint_name)
    if current_clause and _has_required_check_values(current_clause, required_values):
        return
    is_mariadb = bool(getattr(connection.dialect, "is_mariadb", False))
    if current_clause is not None:
        connection.execute(text(_mysql_drop_check_sql(table_name, constraint_name, is_mariadb=is_mariadb)))
    connection.execute(text(_mysql_add_check_sql(table_name, constraint_name, expression)))


def _ensure_approval_cancelled_status_constraint(engine) -> None:
    if engine.dialect.name in {"mysql", "mariadb"}:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        if not {"approval_requests", "approval_steps"}.issubset(table_names):
            return
        with engine.begin() as connection:
            _ensure_mysql_check_constraint(
                connection,
                "approval_requests",
                "ck_approval_requests_status",
                APPROVAL_REQUEST_STATUS_CHECK,
                required_values=("PENDING", "IN_PROGRESS", "APPROVED", "REJECTED", "CANCELLED"),
            )
            _ensure_mysql_check_constraint(
                connection,
                "approval_steps",
                "ck_approval_steps_status",
                APPROVAL_STEP_STATUS_CHECK,
                required_values=("PENDING", "APPROVED", "REJECTED", "CANCELLED"),
            )
        return
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if not {"approval_requests", "approval_steps"}.issubset(table_names):
        return
    with engine.begin() as connection:
        request_sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='approval_requests'")
        ).scalar_one_or_none()
        step_sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='approval_steps'")
        ).scalar_one_or_none()
        if (
            request_sql
            and step_sql
            and "CANCELLED" in request_sql
            and "CANCELLED" in step_sql
        ):
            return

        old_reviews = "approval_task_reviews_old_cancelled_migration"
        old_steps = "approval_steps_old_cancelled_migration"
        old_requests = "approval_requests_old_cancelled_migration"
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        for old_table in (old_reviews, old_steps, old_requests):
            connection.execute(text(f"DROP TABLE IF EXISTS {old_table}"))
        if "approval_task_reviews" in table_names:
            connection.execute(text(f"ALTER TABLE approval_task_reviews RENAME TO {old_reviews}"))
        connection.execute(text(f"ALTER TABLE approval_steps RENAME TO {old_steps}"))
        connection.execute(text(f"ALTER TABLE approval_requests RENAME TO {old_requests}"))
        for old_table in (old_reviews, old_steps, old_requests):
            _drop_sqlite_indexes(connection, old_table)

        ApprovalRequest.__table__.create(bind=connection)
        ApprovalStep.__table__.create(bind=connection)
        if "approval_task_reviews" in table_names:
            ApprovalTaskReview.__table__.create(bind=connection)

        _copy_shared_columns(connection, ApprovalRequest.__table__, old_requests)
        _copy_shared_columns(connection, ApprovalStep.__table__, old_steps)
        if "approval_task_reviews" in table_names:
            _copy_shared_columns(connection, ApprovalTaskReview.__table__, old_reviews)

        for old_table in (old_reviews, old_steps, old_requests):
            connection.execute(text(f"DROP TABLE IF EXISTS {old_table}"))
        connection.execute(text("PRAGMA foreign_keys=ON"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the local development DB.")
    parser.add_argument("--database-url", default="sqlite:///./dev.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    initialize_database(database_url=args.database_url, reset=args.reset)


if __name__ == "__main__":
    main()
