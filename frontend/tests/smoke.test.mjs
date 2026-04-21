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
