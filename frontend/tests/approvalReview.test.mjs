import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { reviewCompletionAction, validateTaskReviewPayload } from "../js/approval.js";

const tasks = [{ id: 1 }, { id: 2 }];
const approvalSource = readFileSync(new URL("../js/approval.js", import.meta.url), "utf8");

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

test("reviewCompletionAction rejects when any item is rejected", () => {
  assert.equal(
    reviewCompletionAction([
      { task_id: 1, decision: "APPROVED", comment: "" },
      { task_id: 2, decision: "REJECTED", comment: "분류 근거 보완" },
    ]),
    "reject",
  );
  assert.equal(
    reviewCompletionAction([
      { task_id: 1, decision: "APPROVED", comment: "" },
      { task_id: 2, decision: "APPROVED", comment: "" },
    ]),
    "approve",
  );
});

test("approval detail exposes a single review completion button", () => {
  assert.match(approvalSource, /data-action="complete-detail"/);
  assert.match(approvalSource, />검토 완료</);
  assert.doesNotMatch(approvalSource, />검토 반려</);
  assert.doesNotMatch(approvalSource, />검토 승인</);
});

test("approval detail opens reject reason modal for reviewed rejections", () => {
  assert.match(approvalSource, /openRejectModal\(approvalId/);
  assert.match(approvalSource, /task_reviews: taskReviews/);
  assert.match(approvalSource, /requested_at/);
});

test("approval view supports direct detail URLs and route navigation", () => {
  assert.match(approvalSource, /params\?\.approvalId/);
  assert.match(approvalSource, /navigateTo\("approver", \{ approvalId \}\)/);
  assert.match(approvalSource, /back-to-approvals/);
});

test("approval list renders subordinate organization status summary", () => {
  assert.match(approvalSource, /\/api\/approvals\/subordinate-status/);
  assert.match(approvalSource, /하위 조직 현황/);
  assert.match(approvalSource, /승인요청 상태/);
  assert.match(approvalSource, /scope_label/);
});
