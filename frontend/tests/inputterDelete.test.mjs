import test from "node:test";
import assert from "node:assert/strict";

import { canDeleteTask } from "../js/spreadsheet.js";

test("canDeleteTask allows admins, creators, and inputters for rejected tasks", () => {
  const task = { id: 10, created_by_employee_id: "part001" };

  assert.equal(canDeleteTask(task, { role: "ADMIN", employee_id: "admin001" }), true);
  assert.equal(canDeleteTask(task, { role: "INPUTTER", employee_id: "part001" }), true);
  assert.equal(canDeleteTask(task, { role: "INPUTTER", employee_id: "other001" }), false);
  assert.equal(
    canDeleteTask(
      { id: 11, status: "REJECTED", created_by_employee_id: "admin001" },
      { role: "INPUTTER", employee_id: "part001" },
    ),
    true,
  );
});
