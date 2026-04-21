import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  filterRejectedTasks,
  hasRejectedTaskReviews,
  hasTaskReviewComments,
  isRejectedTask,
  prioritizeRejectedTasks,
} from "../js/spreadsheet.js";

const spreadsheetSource = readFileSync(new URL("../js/spreadsheet.js", import.meta.url), "utf8");

test("hasTaskReviewComments detects per-task rejection review comments", () => {
  assert.equal(
    hasTaskReviewComments({
      task_reviews: [{ decision: "REJECTED", comment: "보완 필요" }],
    }),
    true,
  );
});

test("hasTaskReviewComments ignores empty review lists", () => {
  assert.equal(hasTaskReviewComments({ task_reviews: [] }), false);
  assert.equal(hasTaskReviewComments({}), false);
});

test("hasRejectedTaskReviews detects rejected task review entries", () => {
  assert.equal(
    hasRejectedTaskReviews({
      task_reviews: [
        { task_id: 1, decision: "APPROVED" },
        { task_id: 2, decision: "REJECTED" },
      ],
    }),
    true,
  );
  assert.equal(hasRejectedTaskReviews({ task_reviews: [{ task_id: 1, decision: "APPROVED" }] }), false);
});

test("filterRejectedTasks keeps only tasks rejected by item review", () => {
  const tasks = [{ id: 1 }, { id: 2 }, { id: 3 }];
  const rejection = {
    task_reviews: [
      { task_id: 1, decision: "APPROVED" },
      { task_id: 2, decision: "REJECTED" },
    ],
  };

  assert.deepEqual(filterRejectedTasks(tasks, rejection), [{ id: 2 }]);
});

test("prioritizeRejectedTasks moves rejected tasks to the top and preserves group order", () => {
  const tasks = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }];
  const rejection = {
    task_reviews: [
      { task_id: 3, decision: "REJECTED" },
      { task_id: 1, decision: "REJECTED" },
      { task_id: 2, decision: "APPROVED" },
    ],
  };

  assert.deepEqual(prioritizeRejectedTasks(tasks, rejection).map((task) => task.id), [1, 3, 2, 4]);
});

test("isRejectedTask identifies rows that need highlight", () => {
  const rejection = { task_reviews: [{ task_id: 7, decision: "REJECTED" }] };

  assert.equal(isRejectedTask({ id: 7 }, rejection), true);
  assert.equal(isRejectedTask({ id: 8 }, rejection), false);
});

test("spreadsheet updates the task table body explicitly when rejection review tables exist", () => {
  assert.match(spreadsheetSource, /data-task-table-body/);
  assert.doesNotMatch(spreadsheetSource, /querySelector\("tbody"\)/);
});

test("spreadsheet marks rejected review rows for visual emphasis", () => {
  assert.match(spreadsheetSource, /rejected-review-row/);
});
