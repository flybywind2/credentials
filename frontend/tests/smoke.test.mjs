import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("frontend shell loads app module and workspace root", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

  assert.match(html, /id="view"/);
  assert.match(html, /type="module"/);
  assert.match(html, /\/js\/app\.js/);
  assert.match(html, /\/css\/style\.css/);
});

test("app module includes login screen state", () => {
  const source = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

  assert.match(source, /login-form/);
  assert.match(source, /credential_employee_id/);
});

test("app module shows a modal when broker organization mapping is missing", () => {
  const source = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

  assert.match(source, /ORG_MAPPING_REQUIRED/);
  assert.match(source, /소속 정보 등록 필요/);
  assert.match(source, /담당자에게 정보 등록을 요청/);
  assert.match(source, /role="dialog"/);
});

test("app module renders a logout action that clears saved authentication", () => {
  const source = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

  assert.match(source, /data-action", "logout"/);
  assert.match(source, /로그아웃/);
  assert.match(source, /logoutCurrentUser\(\)/);
  assert.doesNotMatch(source, /clearEmployeeId\(\)/);
  assert.match(source, /renderLogin\(view, userSummary\)/);
});
