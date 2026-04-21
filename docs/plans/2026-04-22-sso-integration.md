# SSO Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace header-only mock authentication with production-ready LDAP/SAML identity validation and signed bearer-token API authentication while preserving mock-mode developer workflows.

**Architecture:** LDAP and SAML adapters authenticate external identities and return normalized employee ids plus attributes. A user mapping service resolves those identities into app roles and organizations. Auth endpoints issue signed HMAC bearer tokens, and API dependencies prefer bearer tokens while retaining `X-Employee-Id` fallback in mock mode.

**Tech Stack:** FastAPI, SQLAlchemy, stdlib HMAC/base64/json, optional `ldap3`, optional `python3-saml`, pytest, vanilla JavaScript.

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

### Task 2: Provider Adapters

**Files:**
- Modify: `backend/services/sso.py`
- Modify: `backend/tests/test_sso_adapter.py`

**Steps:**
1. Update tests to expect normalized `AuthenticatedIdentity`.
2. Add LDAP fake factory tests for successful bind, missing password, and bind failure.
3. Add SAML fake validator tests for assertion-to-employee mapping.
4. Run adapter tests and confirm RED.
5. Implement mock, LDAP, and SAML adapter methods with dependency injection for tests.
6. Re-run adapter tests and confirm GREEN.

### Task 3: User Mapping And Auth Routes

**Files:**
- Create: `backend/services/user_mapping.py`
- Modify: `backend/routers/auth.py`
- Modify: `backend/dependencies.py`
- Test: `backend/tests/test_auth_login.py`

**Steps:**
1. Add tests for login issuing non-mock bearer token and `/auth/me` resolving it.
2. Add tests for mock-mode `X-Employee-Id` fallback.
3. Add tests for LDAP password field shape and SAML ACS route using monkeypatched adapters.
4. Run auth tests and confirm RED.
5. Implement mapping, token issue, bearer verification, and fallback behavior.
6. Re-run auth tests and confirm GREEN.

### Task 4: Frontend Token Flow

**Files:**
- Modify: `frontend/js/auth.js`
- Modify: `frontend/js/api.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/tests/api.test.mjs`
- Modify: `frontend/tests/smoke.test.mjs`

**Steps:**
1. Add tests for Authorization header injection and login token storage markers.
2. Run frontend tests and confirm RED.
3. Store `credential_access_token` after login and send `Authorization: Bearer`.
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
1. Add environment validation tests for LDAP/SAML-specific required values.
2. Run environment tests and confirm RED.
3. Add config fields and docs for LDAP bind template, SAML SP/IdP metadata, token secret, and admin ids.
4. Re-run backend tests and frontend tests.

### Task 6: Verification

**Files:**
- No production edits expected.

**Steps:**
1. Run `python -m pytest backend/tests`.
2. Run `node --test frontend/tests/*.test.mjs`.
3. Restart local server on port 8000.
4. Run Playwright smoke flow for login, inputter, admin, and approver.
5. Record remaining external dependency gaps: real AD/IdP cannot be verified without environment access.
