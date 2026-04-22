import test from "node:test";
import assert from "node:assert/strict";

import { availableRoutesForRole, routeFromPath, routePathForKey } from "../js/app.js";

test("availableRoutesForRole limits inputters to input workflows", () => {
  assert.deepEqual(availableRoutesForRole("INPUTTER").map((item) => item.key), ["inputter", "status", "group"]);
});

test("availableRoutesForRole gives approvers approval access", () => {
  assert.deepEqual(availableRoutesForRole("APPROVER").map((item) => item.key), ["approver"]);
});

test("availableRoutesForRole gives admins every workspace", () => {
  assert.deepEqual(
    availableRoutesForRole("ADMIN").map((item) => item.key),
    ["inputter", "status", "group", "approver", "admin"],
  );
});

test("routePathForKey returns stable page URLs", () => {
  assert.equal(routePathForKey("inputter"), "/inputter");
  assert.equal(routePathForKey("status"), "/status");
  assert.equal(routePathForKey("group"), "/group");
  assert.equal(routePathForKey("approver"), "/approver");
  assert.equal(routePathForKey("approver", { approvalId: 123 }), "/approver/approvals/123");
  assert.equal(routePathForKey("admin"), "/admin");
});

test("routeFromPath resolves page URLs and approval detail parameters", () => {
  assert.deepEqual(routeFromPath("/"), { key: "inputter", params: {} });
  assert.deepEqual(routeFromPath("/admin"), { key: "admin", params: {} });
  assert.deepEqual(routeFromPath("/approver/approvals/123"), {
    key: "approver",
    params: { approvalId: "123" },
  });
  assert.deepEqual(routeFromPath("/missing"), { key: "inputter", params: {} });
});
