from backend.config import Settings


def validate_runtime_settings(settings: Settings) -> None:
    missing = []
    sso_mode = settings.sso_mode.lower()
    if sso_mode == "ldap":
        for name, value in [
            ("SSO_PROVIDER_URL", settings.sso_provider_url),
            ("SSO_LDAP_BIND_DN_TEMPLATE", settings.sso_ldap_bind_dn_template),
        ]:
            if not value:
                missing.append(name)
        if not settings.sso_token_secret and not settings.sso_client_secret:
            missing.append("SSO_TOKEN_SECRET")
    if sso_mode == "saml":
        for name, value in [
            ("SSO_PROVIDER_URL", settings.sso_provider_url),
            ("SSO_SAML_SP_ENTITY_ID or SSO_CLIENT_ID", settings.sso_saml_sp_entity_id or settings.sso_client_id),
            ("SSO_SAML_ACS_URL", settings.sso_saml_acs_url),
            ("SSO_SAML_IDP_ENTITY_ID", settings.sso_saml_idp_entity_id),
            ("SSO_SAML_SSO_URL", settings.sso_saml_sso_url),
            ("SSO_SAML_X509_CERT", settings.sso_saml_x509_cert),
        ]:
            if not value:
                missing.append(name)
        if not settings.sso_token_secret and not settings.sso_client_secret:
            missing.append("SSO_TOKEN_SECRET")
    if sso_mode == "broker" and not settings.sso_broker_employee_header:
        missing.append("SSO_BROKER_EMPLOYEE_HEADER")
    if sso_mode not in {"mock", "disabled", "broker", "ldap", "saml"}:
        missing.append("SSO_MODE")
    smtp_mode = settings.smtp_mode.lower()
    if smtp_mode == "smtp":
        for name, value in [
            ("SMTP_HOST", settings.smtp_host),
            ("SMTP_USERNAME", settings.smtp_username),
            ("SMTP_PASSWORD", settings.smtp_password),
        ]:
            if not value:
                missing.append(name)
    if smtp_mode == "mail_api":
        for name, value in [
            ("MAIL_API_BASE_URL", settings.mail_api_base_url),
        ]:
            if not value:
                missing.append(name)
    if smtp_mode not in {"disabled", "smtp", "mail_api"}:
        missing.append("SMTP_MODE")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
