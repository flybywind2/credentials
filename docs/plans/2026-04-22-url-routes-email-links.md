# URL Routes And Approval Email Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give every main page a stable browser URL and send approvers directly to their approval detail page from email.

**Architecture:** The frontend remains a vanilla JavaScript SPA, but `app.js` becomes URL-driven through `history.pushState`, `popstate`, and path parsing helpers. FastAPI serves `index.html` for known SPA paths. Approval notification emails include an `APP_BASE_URL`-based detail link.

**Tech Stack:** FastAPI, SQLAlchemy, vanilla ES modules, Node test runner, pytest.

---

### Task 1: Frontend Route Helpers

**Files:**
- Modify: `frontend/js/app.js`
- Test: `frontend/tests/routes.test.mjs`

**Steps:**
1. Add failing tests for `/inputter`, `/status`, `/group`, `/approver`, `/approver/approvals/{id}`, and `/admin`.
2. Export `routePathForKey()` and `routeFromPath()` from `app.js`.
3. Verify route helper tests pass.

### Task 2: URL Driven Navigation

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/approval.js`
- Test: `frontend/tests/approvalReview.test.mjs`

**Steps:**
1. Add failing tests that approval detail URLs are routed through `navigateTo`.
2. Update nav clicks to push browser paths.
3. Make `renderApproval()` open `/approver/approvals/{id}` directly when `approvalId` is present.
4. Support back/forward navigation through `popstate`.

### Task 3: Backend SPA Paths And Email Links

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/config.py`
- Modify: `backend/services/email.py`
- Modify: `backend/routers/approval.py`
- Test: `backend/tests/test_static_frontend.py`
- Test: `backend/tests/test_approval_notifications.py`

**Steps:**
1. Add failing tests for known SPA paths returning `index.html`.
2. Add failing tests that approval request emails include `/approver/approvals/{approval_id}`.
3. Add `APP_BASE_URL`, approval detail URL generation, and HTML action link support.
4. Verify backend tests pass.

### Task 4: Full Verification

**Files:**
- All touched files

**Steps:**
1. Run `python -m pytest backend/tests -q`.
2. Run `node --test frontend/tests/*.test.mjs`.
3. Run `git diff --check`.
4. Use Chrome DevTools to verify direct page URLs and approval detail URL rendering.
