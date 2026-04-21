from pathlib import Path


def test_alembic_configuration_files_exist():
    root = Path(__file__).resolve().parents[2]

    assert (root / "alembic.ini").exists()
    assert (root / "backend" / "migrations" / "env.py").exists()
    assert (root / "backend" / "migrations" / "script.py.mako").exists()
    assert any((root / "backend" / "migrations" / "versions").glob("*.py"))
