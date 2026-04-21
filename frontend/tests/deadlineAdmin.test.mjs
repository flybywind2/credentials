import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { formatDday } from "../js/deadlineAdmin.js";

const deadlineSource = readFileSync(new URL("../js/deadlineAdmin.js", import.meta.url), "utf8");

test("formatDday formats unset, future, today, and overdue deadlines", () => {
  assert.equal(formatDday({ input_deadline: null }), "마감일 미설정");
  assert.equal(formatDday({ input_deadline: "2026-04-30", d_day: 3 }), "D-3");
  assert.equal(formatDday({ input_deadline: "2026-04-30", d_day: 0 }), "D-Day");
  assert.equal(formatDday({ input_deadline: "2026-04-30", d_day: -2 }), "D+2");
});

test("deadline manager includes a description field", () => {
  assert.match(deadlineSource, /name="description"/);
  assert.match(deadlineSource, /description:/);
});
