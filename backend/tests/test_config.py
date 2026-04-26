import os

from backend.config import load_dotenv_file


def test_load_dotenv_file_sets_missing_values_only(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=mysql+pymysql://user:pass@db/credential",
                "SSO_MODE=broker",
                "EXISTING_VALUE=from-file",
                "# ignored",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SSO_MODE", raising=False)
    monkeypatch.setenv("EXISTING_VALUE", "from-env")

    load_dotenv_file(env_file)

    assert os.environ["DATABASE_URL"] == "mysql+pymysql://user:pass@db/credential"
    assert os.environ["SSO_MODE"] == "broker"
    assert os.environ["EXISTING_VALUE"] == "from-env"
