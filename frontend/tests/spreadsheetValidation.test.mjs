import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  firstErrorRow,
  groupValidationErrors,
  previewSelectionSummary,
  selectedPreviewRows,
} from "../js/spreadsheet.js";

const spreadsheetSource = readFileSync(new URL("../js/spreadsheet.js", import.meta.url), "utf8");

test("groupValidationErrors groups backend cell errors by row", () => {
  const grouped = groupValidationErrors([
    { row_index: 2, field: "major_task", message: "대업무 필수" },
    { row_index: 2, field: "detail_task", message: "세부업무 필수" },
    { row_index: 0, field: "organization_id", message: "권한 없음" },
  ]);

  assert.equal(grouped.get(2).length, 2);
  assert.equal(grouped.get(0)[0].field, "organization_id");
});

test("firstErrorRow returns the earliest row index", () => {
  assert.equal(firstErrorRow([{ row_index: 5 }, { row_index: 1 }]), 1);
  assert.equal(firstErrorRow([]), null);
});

test("spreadsheet source includes approval confirmation and excel preview flow", () => {
  assert.match(spreadsheetSource, /approval-confirm-modal/);
  assert.match(spreadsheetSource, /\/api\/tasks\/import\/preview/);
  assert.match(spreadsheetSource, /data-action="save-all"/);
  assert.match(spreadsheetSource, /data-action="preview-save-selected"/);
  assert.match(spreadsheetSource, /data-action="preview-save-all"/);
});

test("spreadsheet source marks fixed columns for sticky layout", () => {
  assert.match(spreadsheetSource, /sticky-col sticky-no/);
  assert.match(spreadsheetSource, /sticky-col sticky-sub-part/);
  assert.match(spreadsheetSource, /sticky-col sticky-major-task/);
  assert.match(spreadsheetSource, /sticky-col sticky-detail-task/);
});

test("previewSelectionSummary counts valid, invalid, and selected rows", () => {
  const rows = [{ id: 1 }, { id: 2 }, { id: 3 }];
  const groupedErrors = new Map([[1, [{ message: "대업무 필수" }]]]);
  const selectedIndexes = new Set([0, 1, 2]);

  assert.deepEqual(previewSelectionSummary(rows, groupedErrors, selectedIndexes), {
    total: 3,
    valid: 2,
    errorRows: 1,
    selectedValid: 2,
  });
});

test("selectedPreviewRows returns only checked valid rows", () => {
  const rows = [{ major_task: "저장" }, { major_task: "오류" }, { major_task: "미선택" }];
  const groupedErrors = new Map([[1, [{ message: "세부업무 필수" }]]]);
  const selectedIndexes = new Set([0, 1]);

  assert.deepEqual(selectedPreviewRows(rows, groupedErrors, selectedIndexes), [
    { major_task: "저장" },
  ]);
});
