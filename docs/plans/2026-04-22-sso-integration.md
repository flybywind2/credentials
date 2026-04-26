# SSO Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support local mock login and production company SSO broker authentication without letting browser-controlled values override broker identity.

**Architecture:** `MockSsoAdapter` supports direct local testing. `BrokerSsoAdapter` reads trusted internal headers. A user mapping service resolves employee ids into app roles and organizations. API dependencies use mock cookies/tokens only in mock mode and broker headers only in broker mode.

**Tech Stack:** FastAPI, SQLAlchemy, stdlib HMAC/base64/json, pytest, vanilla JavaScript.

---

### Task 1: Token Service

**Files:**
- Create: `backend/services/auth_tokens.py`
- Test: `backend/tests/test_auth_tokens.py`

**Steps:**
1. Write tests for token round trip, tamper rejection, and expiration rejection.
2. Run `python -m pytest backend/tests/test_auth_tokens.py -q` and confirm RED.
3. Implement `create_access_token(user, expires_in_seconds=None)` and `verify_access_token(token)`.
4. Re-run the token test and confirm GREEN.

### Task 2: SSO Adapters

**Files:**
- Modify: `backend/services/sso.py`
- Modify: `backend/tests/test_sso_adapter.py`

**Steps:**
1. Update tests to expect normalized `AuthenticatedIdentity`.
2. Add mock adapter tests for employee id normalization.
3. Add broker adapter tests for configured header names and optional user attributes.
4. Run adapter tests and confirm RED.
5. Implement mock and broker adapter methods with dependency injection for tests.
6. Re-run adapter tests and confirm GREEN.

### Task 3: User Mapping And Auth Routes

**Files:**
- Create: `backend/services/user_mapping.py`
- Modify: `backend/routers/auth.py`
- Modify: `backend/dependencies.py`
- Test: `backend/tests/test_auth_login.py`

**Steps:**
1. Add tests for mock login issuing a bearer token and `/auth/me` resolving it.
2. Add tests for mock-mode `X-Employee-Id` fallback.
3. Add tests for broker mode requiring broker employee header.
4. Add tests that stale mock tokens do not override broker users.
5. Run auth tests and confirm RED.
6. Implement mapping, token issue, broker header verification, and fallback behavior.
7. Re-run auth tests and confirm GREEN.

### Task 4: Frontend Mock Flow

**Files:**
- Modify: `frontend/js/auth.js`
- Modify: `frontend/js/api.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/tests/api.test.mjs`
- Modify: `frontend/tests/smoke.test.mjs`

**Steps:**
1. Add tests for Authorization header injection and mock user cookie markers.
2. Run frontend tests and confirm RED.
3. Store `credential_access_token` and mock employee cookie after local login.
4. Keep `credential_employee_id` for mock compatibility.
5. Re-run frontend tests and confirm GREEN.

### Task 5: Config And Docs

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/services/environment.py`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`
- Modify: `docs/sso-mysql-setup.md`
- Modify: `README.md`
- Modify: `tasks.md`

**Steps:**
1. Add environment validation tests for supported and unsupported SSO modes.
2. Run environment tests and confirm RED.
3. Add config fields and docs for broker headers, token secret, and admin ids.
4. Re-run backend tests and frontend tests.

### Task 6: Verification

**Files:**
- No production edits expected.

**Steps:**
1. Run `python -m pytest backend/tests`.
2. Run `node --test frontend/tests/*.test.mjs`.
3. Restart local server on port 8000.
4. Run browser smoke flow for login, inputter, admin, and approver.
5. Record remaining external dependency gaps: real SSO broker cannot be verified without environment access.
