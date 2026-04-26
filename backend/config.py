import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip("'\"")
        os.environ[key] = value


load_dotenv_file()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    app_base_url: str = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
    sso_mode: str = os.getenv("SSO_MODE", "mock")
    sso_token_secret: str = os.getenv("SSO_TOKEN_SECRET", "")
    sso_token_expire_minutes: int = int(os.getenv("SSO_TOKEN_EXPIRE_MINUTES", "480"))
    sso_admin_employee_ids: str = os.getenv("SSO_ADMIN_EMPLOYEE_IDS", "admin001")
    sso_broker_employee_header: str = os.getenv("SSO_BROKER_EMPLOYEE_HEADER", "X-Broker-Employee-Id")
    sso_broker_name_header: str = os.getenv("SSO_BROKER_NAME_HEADER", "")
    sso_broker_email_header: str = os.getenv("SSO_BROKER_EMAIL_HEADER", "")
    sso_broker_dept_header: str = os.getenv("SSO_BROKER_DEPT_HEADER", "deptname")
    mail_mode: str = os.getenv("MAIL_MODE", "disabled")
    mail_api_base_url: str = os.getenv("MAIL_API_BASE_URL", "mail.net")
    mail_api_system_id: str = os.getenv("MAIL_API_SYSTEM_ID", "")
    mail_api_timeout_seconds: float = float(os.getenv("MAIL_API_TIMEOUT_SECONDS", "10"))


settings = Settings()
