import test from "node:test";
import assert from "node:assert/strict";

import { buildTaskFilterQuery, formatLatestReview } from "../js/adminTaskQuery.js";

test("buildTaskFilterQuery omits empty filters", () => {
  assert.equal(
    buildTaskFilterQuery({ part: "AI", status: "DRAFT", division: "", is_confidential: "true" }),
    "part=AI&status=DRAFT&is_confidential=true",
  );
});

test("formatLatestReview summarizes the latest task review", () => {
  assert.deepEqual(
    formatLatestReview({
      decision: "REJECTED",
      comment: "근거 보완 필요",
      reviewer_employee_id: "div001",
    }),
    {
      decision: "반려",
      comment: "근거 보완 필요",
      reviewer: "div001",
    },
  );
});

test("formatLatestReview returns dashes when no review exists", () => {
  assert.deepEqual(formatLatestReview(null), {
    decision: "-",
    comment: "-",
    reviewer: "-",
  });
});
