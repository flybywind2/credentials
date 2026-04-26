from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql

from backend.database import Base
from backend.scripts.init_db import _mysql_drop_check_sql
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
