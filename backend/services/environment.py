from backend.config import Settings


def validate_runtime_settings(settings: Settings) -> None:
    missing = []
    if settings.sso_mode.lower() not in {"mock", "disabled"}:
        for name, value in [
            ("SSO_PROVIDER_URL", settings.sso_provider_url),
            ("SSO_CLIENT_ID", settings.sso_client_id),
            ("SSO_CLIENT_SECRET", settings.sso_client_secret),
        ]:
            if not value:
                missing.append(name)
    if settings.smtp_mode.lower() == "smtp":
        for name, value in [
            ("SMTP_HOST", settings.smtp_host),
            ("SMTP_USERNAME", settings.smtp_username),
            ("SMTP_PASSWORD", settings.smtp_password),
        ]:
            if not value:
                missing.append(name)
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
