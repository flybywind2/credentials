import test from "node:test";
import assert from "node:assert/strict";

import { validateTaskReviewPayload } from "../js/approval.js";

const tasks = [{ id: 1 }, { id: 2 }];

test("validateTaskReviewPayload requires every task to be reviewed", () => {
  const result = validateTaskReviewPayload(tasks, [{ task_id: 1, decision: "APPROVED", comment: "" }], "approve");

  assert.equal(result.valid, false);
  assert.match(result.message, /모든 항목/);
});

test("validateTaskReviewPayload blocks approve when any task is rejected", () => {
  const result = validateTaskReviewPayload(
    tasks,
    [
      { task_id: 1, decision: "APPROVED", comment: "" },
      { task_id: 2, decision: "REJECTED", comment: "분류 재검토" },
    ],
    "approve",
  );

  assert.equal(result.valid, false);
  assert.match(result.message, /승인/);
});

test("validateTaskReviewPayload requires a comment for rejected items", () => {
  const result = validateTaskReviewPayload(
    tasks,
    [
      { task_id: 1, decision: "APPROVED", comment: "" },
      { task_id: 2, decision: "REJECTED", comment: "" },
    ],
    "reject",
  );

  assert.equal(result.valid, false);
  assert.match(result.message, /의견/);
});

test("validateTaskReviewPayload accepts a complete rejection review", () => {
  const result = validateTaskReviewPayload(
    tasks,
    [
      { task_id: 1, decision: "APPROVED", comment: "" },
      { task_id: 2, decision: "REJECTED", comment: "분류 근거 보완" },
    ],
    "reject",
  );

  assert.equal(result.valid, true);
});
