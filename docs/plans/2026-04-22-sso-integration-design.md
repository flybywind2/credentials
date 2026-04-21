# SSO Integration Design

## Context

The app currently supports `SSO_MODE=mock`, `ldap`, and `saml`, but LDAP/SAML modes only validate configuration and then map seed users. Browser login stores an employee id and API calls trust `X-Employee-Id`. That is acceptable for local development, but not for production.

## Design

Implement production SSO as a two-step boundary:

1. Provider adapters authenticate an external identity.
   - LDAP performs an AD bind through `ldap3` using `employee_id` and password.
   - SAML validates a SAML Response through `python3-saml` and extracts the employee id attribute.
2. The app maps the authenticated employee id to an application user.
   - Existing seed/mock users still work.
   - Unknown employee ids are resolved from `organizations` by head ids.
   - Admin ids can be supplied through `SSO_ADMIN_EMPLOYEE_IDS`.

After login, the backend issues a signed bearer token. API dependencies prefer `Authorization: Bearer ...`; the legacy `X-Employee-Id` header remains available only in mock mode for local tests and development.

## Error Handling

- Bad LDAP credentials or invalid SAML assertions return `401`.
- Missing provider configuration returns `500` at authentication time or startup validation.
- Unknown authenticated employee ids return `404` unless they map to organization head ids or admin ids.
- Tampered or expired bearer tokens return `401`.

## Testing

Provider tests use injected fake LDAP/SAML validators so CI does not need a real AD or IdP. Token tests verify round trip, tamper rejection, and `/api/auth/me` bearer behavior. Existing mock-header tests remain valid.
