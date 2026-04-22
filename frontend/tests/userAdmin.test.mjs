import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { filterUserRows, roleLabel } from "../js/userAdmin.js";

const dashboardSource = readFileSync(new URL("../js/dashboard.js", import.meta.url), "utf8");
const userAdminSource = readFileSync(new URL("../js/userAdmin.js", import.meta.url), "utf8");

test("roleLabel renders Korean labels for app roles", () => {
  assert.equal(roleLabel("ADMIN"), "관리자");
  assert.equal(roleLabel("INPUTTER"), "입력자");
  assert.equal(roleLabel("APPROVER"), "승인자");
});

test("filterUserRows searches employee, name, role, and organization text", () => {
  const users = [
    { employee_id: "admin001", name: "관리자", role: "ADMIN", organization_path: "AI실 / AI팀" },
    { employee_id: "part001", name: "최파트장", role: "INPUTTER", organization_path: "보안실 / 관제파트" },
  ];

  assert.deepEqual(filterUserRows(users, "보안").map((user) => user.employee_id), ["part001"]);
  assert.deepEqual(filterUserRows(users, "관리자").map((user) => user.employee_id), ["admin001"]);
  assert.equal(filterUserRows(users, "").length, 2);
});

test("dashboard mounts the user permission manager", () => {
  assert.match(dashboardSource, /renderUserManager/);
  assert.match(dashboardSource, /user-manager-root/);
});

test("user permission manager uses admin user APIs and exposes role controls", () => {
  assert.match(userAdminSource, /\/api\/admin\/users/);
  assert.match(userAdminSource, /data-user-form/);
  assert.match(userAdminSource, /name="role"/);
  assert.match(userAdminSource, /data-action="edit-user"/);
  assert.match(userAdminSource, /data-action="delete-user"/);
});
