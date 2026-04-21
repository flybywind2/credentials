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
