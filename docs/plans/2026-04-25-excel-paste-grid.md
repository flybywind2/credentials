# Excel Paste Grid Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the raw TSV textarea paste workflow with a cleaner Excel paste grid that accepts copied Excel cells and shows only structured preview rows.

**Architecture:** Keep the current task import contract: only `소파트`, `대업무`, `세부업무` are accepted and imported as `UPLOADED` rows for later web classification. Add a clipboard parser that prefers Excel `text/html` tables and falls back to existing `text/plain` TSV. Update the paste modal to use a visible paste target and preview table instead of exposing raw TSV text.

**Tech Stack:** Vanilla JavaScript modules, Node `node:test`, existing FastAPI validation endpoint `/api/tasks/validate`, existing CSS modal/table styles.

---

### Task 1: Parser Contract

**Files:**
- Modify: `frontend/js/clipboard.js`
- Test: `frontend/tests/clipboard.test.mjs`

**Step 1: Write failing tests**

Add tests for `parseClipboardToTasks({ html, text }, questions, { organizationId })`:
- Parses Excel-style HTML table rows with Korean headers.
- Falls back to TSV when HTML is missing.

**Step 2: Run test to verify failure**

Run: `node --test frontend\tests\clipboard.test.mjs`

Expected: fail because `parseClipboardToTasks` is not exported.

**Step 3: Implement minimal parser**

Implement:
- `parseHtmlTableRows(html)` using `DOMParser` when available.
- Fallback cell extraction for Node tests.
- `parseClipboardToTasks(payload, questions, options)` that prefers HTML rows and falls back to `parseTsvToTasks`.

**Step 4: Run parser tests**

Run: `node --test frontend\tests\clipboard.test.mjs`

Expected: pass.

### Task 2: Paste Modal UI

**Files:**
- Modify: `frontend/js/spreadsheet.js`
- Modify: `frontend/css/style.css`
- Test: `frontend/tests/spreadsheetValidation.test.mjs`

**Step 1: Write failing source-level tests**

Assert the spreadsheet source:
- Uses `parseClipboardToTasks`.
- Shows `Excel 붙여넣기`.
- Does not show a user-facing `TSV 데이터` label.
- Handles `text/html` in paste events.

**Step 2: Run test to verify failure**

Run: `node --test frontend\tests\spreadsheetValidation.test.mjs`

Expected: fail on missing parser/UI strings.

**Step 3: Implement modal**

Replace raw textarea with:
- Paste target box.
- Preview result table.
- Optional pasted-row count/status.
- Paste listener on the target using `clipboardData.getData("text/html")` and `text/plain`.

Keep existing save selected/all behavior and backend validation.

**Step 4: Run spreadsheet tests**

Run: `node --test frontend\tests\spreadsheetValidation.test.mjs`

Expected: pass.

### Task 3: Verification

**Files:**
- Modify: `test_results.md`

**Step 1: Run frontend tests**

Run: `node --test frontend\tests\*.test.mjs`

Expected: all pass.

**Step 2: Run backend regression**

Run: `python -m pytest backend\tests -q -p no:cacheprovider`

Expected: all pass.

**Step 3: Browser check**

Use the in-app browser:
- Open `/inputter`.
- Click `Excel 붙여넣기`.
- Confirm paste target and preview buttons render.
- Confirm console error log is empty.

**Step 4: Update test results**

Add the UI paste-grid verification to `test_results.md`.
