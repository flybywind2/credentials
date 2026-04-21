import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    sso_mode: str = os.getenv("SSO_MODE", "mock")
    sso_provider_url: str = os.getenv("SSO_PROVIDER_URL", "")
    sso_client_id: str = os.getenv("SSO_CLIENT_ID", "")
    sso_client_secret: str = os.getenv("SSO_CLIENT_SECRET", "")
    smtp_mode: str = os.getenv("SMTP_MODE", "disabled")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")


settings = Settings()
