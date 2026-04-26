from backend.config import Settings


def validate_runtime_settings(settings: Settings) -> None:
    missing = []
    sso_mode = settings.sso_mode.lower()
    if sso_mode == "broker":
        if not settings.broker_url:
            missing.append("BROKER_URL")
        if not settings.service_url:
            missing.append("SERVICE_URL")
        if not settings.sso_broker_employee_header:
            missing.append("SSO_BROKER_EMPLOYEE_HEADER")
    if sso_mode not in {"mock", "broker"}:
        missing.append("SSO_MODE")
    mail_mode = settings.mail_mode.lower()
    if mail_mode == "mail_api":
        for name, value in [
            ("MAIL_API_BASE_URL", settings.mail_api_base_url),
        ]:
            if not value:
                missing.append(name)
    if mail_mode not in {"disabled", "mail_api"}:
        missing.append("MAIL_MODE")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
