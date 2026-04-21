import test from "node:test";
import assert from "node:assert/strict";

import { availableRoutesForRole } from "../js/app.js";

test("availableRoutesForRole limits inputters to input workflows", () => {
  assert.deepEqual(availableRoutesForRole("INPUTTER").map((item) => item.key), ["inputter", "group"]);
});

test("availableRoutesForRole gives approvers approval access", () => {
  assert.deepEqual(availableRoutesForRole("APPROVER").map((item) => item.key), ["approver"]);
});

test("availableRoutesForRole gives admins every workspace", () => {
  assert.deepEqual(
    availableRoutesForRole("ADMIN").map((item) => item.key),
    ["inputter", "group", "approver", "admin"],
  );
});
