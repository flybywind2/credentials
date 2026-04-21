# P1 Gap Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement remaining P1 audit gaps for S05 preview UX and TRD API compatibility.

**Architecture:** Extend existing modules without introducing new routers or frontend frameworks. Reuse current task creation, deadline serialization, export filtering, and preview validation code paths.

**Tech Stack:** FastAPI, SQLAlchemy, vanilla JavaScript, pytest, Node.js test runner.

---

### Task 1: API Compatibility

**Files:**
- Modify: `backend/routers/task.py`
- Modify: `backend/routers/settings.py`
- Modify: `backend/routers/export.py`
- Test: backend tests for task bulk, deadline aliases, and export alias.

**Steps:**
1. Write failing tests for `POST /api/tasks/bulk`, `GET/POST /api/admin/deadline`, and `approval_status` export filtering.
2. Run targeted tests and confirm RED.
3. Implement aliases by reusing existing helper functions and permission checks.
4. Run targeted tests and confirm GREEN.

### Task 2: S05 Preview UX

**Files:**
- Modify: `frontend/js/spreadsheet.js`
- Test: `frontend/tests/spreadsheetValidation.test.mjs`

**Steps:**
1. Write failing frontend tests for selectable valid preview rows and save-all valid rows controls.
2. Run targeted frontend tests and confirm RED.
3. Add checkbox selection, selected count, selected save, and all-valid save behavior.
4. Run targeted frontend tests and confirm GREEN.

### Task 3: Tasks And Verification

**Files:**
- Modify: `tasks.md`

**Steps:**
1. Mark completed P1 audit items.
2. Run full backend tests.
3. Run full frontend tests.
4. Commit and push final changes.
