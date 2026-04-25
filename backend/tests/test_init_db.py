from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.models import (
    ApprovalRequest,
    ConfidentialQuestion,
    NationalTechQuestion,
    Organization,
    TaskEntry,
    User,
)
from backend.scripts.init_db import initialize_database


def test_initialize_database_rebuilds_and_seeds_sqlite_db(tmp_path: Path):
    db_path = tmp_path / "local.db"
    database_url = f"sqlite:///{db_path}"

    initialize_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    session = sessionmaker(bind=engine)()
    try:
        assert session.scalar(select(Organization).limit(1)).part_name == "AI전략실행파트"
        assert session.scalar(select(User).limit(1)).email == "admin001@samsung.com"
        assert session.scalar(select(TaskEntry).limit(1)).major_task == "기밀 분류 체계 수립"
        assert session.scalar(select(ConfidentialQuestion).limit(1)).options == ["해당 없음", "해당 됨"]
        assert session.scalar(select(NationalTechQuestion).limit(1)).options == ["해당 없음", "해당 됨"]
        assert session.scalar(select(ApprovalRequest).limit(1)).total_steps == 3
    finally:
        session.close()
