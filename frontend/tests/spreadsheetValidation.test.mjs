import test from "node:test";
import assert from "node:assert/strict";

import { firstErrorRow, groupValidationErrors } from "../js/spreadsheet.js";

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
