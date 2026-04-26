import test from "node:test";
import assert from "node:assert/strict";

import {
  classificationDonutStyle,
  classificationSummaryFromTasks,
} from "../js/classificationChart.js";

test("classificationSummaryFromTasks counts tasks with any classification flag as applicable", () => {
  const summary = classificationSummaryFromTasks([
    { is_confidential: false, is_national_tech: false, is_compliance: false },
    { is_confidential: true, is_national_tech: false, is_compliance: false },
    { is_confidential: false, is_national_tech: true, is_compliance: false },
    { is_confidential: false, is_national_tech: false, is_compliance: true },
  ]);

  assert.deepEqual(summary, {
    total: 4,
    applicable: 3,
    not_applicable: 1,
  });
});

test("classificationDonutStyle renders an applicable versus not applicable conic gradient", () => {
  assert.match(
    classificationDonutStyle({ total: 4, applicable: 3, not_applicable: 1 }),
    /conic-gradient/,
  );
  assert.equal(
    classificationDonutStyle({ total: 0, applicable: 0, not_applicable: 0 }),
    "background: #eee8f8",
  );
});
