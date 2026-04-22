# Internal Mail API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `mail_api` delivery mode that sends approval email through the company mail API.

**Architecture:** Keep `EmailService` as the delivery boundary. `get_email_service()` selects `DisabledEmailService`, `SmtpEmailService`, or `MailApiEmailService` based on `SMTP_MODE`. The mail API sender maps `EmailMessage` into the company request contract and posts through `httpx`.

**Tech Stack:** FastAPI, Python 3.10, dataclass settings, `httpx`, pytest.

---

### Task 1: Mail API Tests

**Files:**
- Modify: `backend/tests/test_email_and_environment.py`

**Step 1: Write failing tests**

Add tests that expect:
- `MailApiEmailService.send()` posts to `/send_mail`.
- JSON mode includes `subject`, `docSecuType`, `contents`, `contentType`, and `recipients`.
- Optional `MAIL_API_SYSTEM_ID` is sent as request header `System-ID`.
- Form mode sends `data` instead of `json`.
- Runtime validation requires mail API settings when `SMTP_MODE=mail_api`.

**Step 2: Run RED**

Run:

```powershell
python -m pytest backend/tests/test_email_and_environment.py -q
```

Expected: fails because `MailApiEmailService` and settings do not exist.

### Task 2: Mail API Implementation

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/services/email.py`
- Modify: `backend/services/environment.py`

**Step 1: Add settings**

Add `MAIL_API_*` settings with safe defaults.

**Step 2: Implement service**

Create `MailApiEmailService` using `httpx.post()`, map message fields to the internal API contract, support JSON and form payloads, and call `raise_for_status()`.

**Step 3: Select mode**

Return `MailApiEmailService` from `get_email_service()` when `SMTP_MODE=mail_api`.

**Step 4: Run GREEN**

Run:

```powershell
python -m pytest backend/tests/test_email_and_environment.py -q
```

Expected: all tests pass.

### Task 3: Environment And Deployment Docs

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/sso-mysql-setup.md`
- Modify: `k8s/configmap.yaml`
- Modify: `k8s/secret.example.yaml`
- Modify: `docker/docker-compose.private-cloud.yml`

**Step 1: Document variables**

Add `MAIL_API_*` examples and explain `SMTP_MODE=mail_api`.

**Step 2: Run full verification**

Run:

```powershell
python -m pytest backend/tests -q
node --test frontend/tests/*.test.mjs
git diff --check
```

Expected: all tests pass and diff check reports no whitespace errors.
