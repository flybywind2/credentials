import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    app_base_url: str = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
    sso_mode: str = os.getenv("SSO_MODE", "mock")
    sso_provider_url: str = os.getenv("SSO_PROVIDER_URL", "")
    sso_client_id: str = os.getenv("SSO_CLIENT_ID", "")
    sso_client_secret: str = os.getenv("SSO_CLIENT_SECRET", "")
    sso_token_secret: str = os.getenv("SSO_TOKEN_SECRET", "")
    sso_token_expire_minutes: int = int(os.getenv("SSO_TOKEN_EXPIRE_MINUTES", "480"))
    sso_admin_employee_ids: str = os.getenv("SSO_ADMIN_EMPLOYEE_IDS", "admin001")
    sso_ldap_bind_dn_template: str = os.getenv("SSO_LDAP_BIND_DN_TEMPLATE", "{employee_id}")
    sso_ldap_search_base: str = os.getenv("SSO_LDAP_SEARCH_BASE", "")
    sso_ldap_search_filter: str = os.getenv(
        "SSO_LDAP_SEARCH_FILTER",
        "(sAMAccountName={employee_id})",
    )
    sso_ldap_employee_attr: str = os.getenv("SSO_LDAP_EMPLOYEE_ATTR", "sAMAccountName")
    sso_ldap_name_attr: str = os.getenv("SSO_LDAP_NAME_ATTR", "displayName")
    sso_saml_sp_entity_id: str = os.getenv("SSO_SAML_SP_ENTITY_ID", "")
    sso_saml_acs_url: str = os.getenv("SSO_SAML_ACS_URL", "")
    sso_saml_idp_entity_id: str = os.getenv("SSO_SAML_IDP_ENTITY_ID", "")
    sso_saml_sso_url: str = os.getenv("SSO_SAML_SSO_URL", "")
    sso_saml_x509_cert: str = os.getenv("SSO_SAML_X509_CERT", "")
    sso_saml_employee_attr: str = os.getenv("SSO_SAML_EMPLOYEE_ATTR", "employee_id")
    smtp_mode: str = os.getenv("SMTP_MODE", "disabled")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    mail_api_base_url: str = os.getenv("MAIL_API_BASE_URL", "mail.net")
    mail_api_system_id: str = os.getenv("MAIL_API_SYSTEM_ID", "")
    mail_api_doc_secu_type: str = os.getenv("MAIL_API_DOC_SECU_TYPE", "PERSONAL")
    mail_api_content_type: str = os.getenv("MAIL_API_CONTENT_TYPE", "HTML")
    mail_api_payload_format: str = os.getenv("MAIL_API_PAYLOAD_FORMAT", "json")
    mail_api_recipient_type: str = os.getenv("MAIL_API_RECIPIENT_TYPE", "TO")
    mail_api_timeout_seconds: float = float(os.getenv("MAIL_API_TIMEOUT_SECONDS", "10"))


settings = Settings()
