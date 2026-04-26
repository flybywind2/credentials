# SSO Integration Design

## Context

The app supports `SSO_MODE=mock` for local development and `SSO_MODE=broker` for production. Browser login stores the selected employee id only in mock mode. Production requests are authenticated by the company SSO broker before they reach the app.

## Design

Implement production SSO as a broker boundary:

1. The company SSO broker or reverse proxy authenticates the user.
2. The broker strips any external user headers and injects trusted internal headers.
3. The app reads the configured employee header and optional name, email, and `deptname` headers.
4. The app maps the employee id to application roles and organizations.

The backend keeps signed bearer tokens for mock login convenience, but broker mode does not let stale browser tokens override the broker user.

## Error Handling

- Missing broker employee header returns `401`.
- Unknown authenticated employee ids return `404` unless they map to organization head ids or admin ids.
- `deptname` that cannot identify exactly one organization returns `409 ORG_MAPPING_REQUIRED`.
- Tampered or expired mock bearer tokens return `401`.

## Testing

Tests verify mock login, broker header resolution, stale-token precedence, user mapping, `deptname` organization resolution, and rejection of unsupported SSO modes.
