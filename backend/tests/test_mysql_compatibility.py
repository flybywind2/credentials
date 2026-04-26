from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql

from backend.database import Base
from backend.scripts.init_db import (
    TASK_ENTRY_STATUS_CHECK,
    TASK_ENTRY_STATUS_VALUES,
    _ensure_mysql_check_constraint,
    _mysql_drop_check_sql,
)
import backend.models  # noqa: F401


def test_all_tables_compile_with_mysql_dialect():
    dialect = mysql.dialect()

    compiled_tables = [
        str(CreateTable(table).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
    ]

    assert compiled_tables
    assert any("JSON" in ddl for ddl in compiled_tables)
    assert any("DATETIME" in ddl for ddl in compiled_tables)
    assert all("CHECK" in ddl or "CREATE TABLE" in ddl for ddl in compiled_tables)


def test_mysql_drop_check_sql_uses_dialect_specific_syntax():
    assert (
        _mysql_drop_check_sql("approval_requests", "ck_approval_requests_status", is_mariadb=False)
        == "ALTER TABLE `approval_requests` DROP CHECK `ck_approval_requests_status`"
    )
    assert (
        _mysql_drop_check_sql("approval_requests", "ck_approval_requests_status", is_mariadb=True)
        == "ALTER TABLE `approval_requests` DROP CONSTRAINT `ck_approval_requests_status`"
    )


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDialect:
    name = "mysql"
    is_mariadb = False


class _FakeConnection:
    dialect = _FakeDialect()

    def __init__(self, current_clause):
        self.current_clause = current_clause
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        if "information_schema.check_constraints" in sql:
            return _ScalarResult(self.current_clause)
        self.statements.append(sql)
        return _ScalarResult(None)


def test_mysql_task_entry_status_constraint_adds_uploaded_to_existing_db():
    connection = _FakeConnection("`status` in ('DRAFT','SUBMITTED','APPROVED','REJECTED')")

    _ensure_mysql_check_constraint(
        connection,
        "task_entries",
        "ck_task_entries_status",
        TASK_ENTRY_STATUS_CHECK,
        required_values=TASK_ENTRY_STATUS_VALUES,
    )

    assert connection.statements == [
        "ALTER TABLE `task_entries` DROP CHECK `ck_task_entries_status`",
        (
            "ALTER TABLE `task_entries` ADD CONSTRAINT `ck_task_entries_status` "
            "CHECK (status in ('UPLOADED', 'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'))"
        ),
    ]


def test_mysql_task_entry_status_constraint_is_left_when_uploaded_exists():
    connection = _FakeConnection("`status` in ('UPLOADED','DRAFT','SUBMITTED','APPROVED','REJECTED')")

    _ensure_mysql_check_constraint(
        connection,
        "task_entries",
        "ck_task_entries_status",
        TASK_ENTRY_STATUS_CHECK,
        required_values=TASK_ENTRY_STATUS_VALUES,
    )

    assert connection.statements == []
