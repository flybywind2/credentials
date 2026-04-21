from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql

from backend.database import Base
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
