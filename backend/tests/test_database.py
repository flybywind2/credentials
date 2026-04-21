from sqlalchemy import text

from backend.database import SessionLocal, engine


def test_database_engine_can_execute_sql():
    with engine.connect() as connection:
        result = connection.execute(text("select 1")).scalar_one()

    assert result == 1


def test_database_session_can_execute_sql():
    db = SessionLocal()
    try:
        result = db.execute(text("select 1")).scalar_one()
    finally:
        db.close()

    assert result == 1
