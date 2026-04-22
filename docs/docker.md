# Docker Runbook

## Local Container Run

The Docker image is pinned to Python `3.10.19` through `docker/Dockerfile`.

Run the app from the repository root:

```powershell
docker compose -f docker/docker-compose.yml up --build
```

The container serves the FastAPI API and static frontend on one port:

- App URL: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/api/health`

## Configuration

The compose file uses local MVP defaults:

```yaml
DATABASE_URL: sqlite:///./dev.db
SSO_MODE: mock
SMTP_MODE: disabled
```

Use `.env.example` as the template for environment-specific values. Do not place real SSO, mail API, SMTP, or production database secrets in the repository.

## Private Cloud Run

Create `.env.private-cloud` outside source control from `.env.example`, then set production values for `DATABASE_URL`, `APP_BASE_URL`, `SSO_MODE`, `SSO_PROVIDER_URL`, `SSO_TOKEN_SECRET`, the LDAP or SAML mode-specific variables, and the `MAIL_API_*` values. Use `SMTP_MODE=mail_api` for the company mail gateway. The app posts to `{MAIL_API_BASE_URL}/send_mail`; `MAIL_API_BASE_URL=mail.net` resolves to `https://mail.net/send_mail`.

Run the private-cloud profile from the repository root:

```powershell
docker compose -f docker/docker-compose.private-cloud.yml up --build -d
```

When `SSO_MODE=ldap` or `SSO_MODE=saml`, startup validates the required SSO environment variables and fails fast with the missing names. LDAP uses `ldap3` bind; SAML uses `python3-saml` ACS validation. See `docs/sso-mysql-setup.md` for the full SSO and MySQL setup guide.

## Reset Local Data

Inside a running container or local Python environment, recreate the SQLite tables and seed data with:

```powershell
python -m backend.scripts.init_db --reset
```

## Stop

```powershell
docker compose -f docker/docker-compose.yml down
```
