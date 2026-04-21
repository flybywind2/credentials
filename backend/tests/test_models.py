from backend.database import Base, engine
import backend.models  # noqa: F401


def test_model_tables_are_registered():
    Base.metadata.create_all(bind=engine)
    assert "organizations" in Base.metadata.tables
    assert "task_entries" in Base.metadata.tables
    assert "approval_requests" in Base.metadata.tables
