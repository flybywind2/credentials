import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../css/style.css", import.meta.url), "utf8");
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("frontend shell uses the review stylesheet", () => {
  assert.match(html, /style\.css\?v=20260422-user-permissions/);
});

test("desktop layout fills the viewport and keeps a desktop minimum width", () => {
  assert.match(css, /body\s*\{[\s\S]*min-width:\s*1280px;/);
  assert.match(css, /#app\s*\{[\s\S]*height:\s*100vh;/);
  assert.match(css, /\.view\s*\{[\s\S]*overflow:\s*hidden;/);
});

test("mobile-specific responsive branch is removed", () => {
  assert.doesNotMatch(css, /@media\s*\(\s*max-width:/);
});

test("modal overlay sits above sticky data-table columns", () => {
  const stickyHeaderZ = Number(css.match(/\.data-table th\.sticky-col\s*\{[\s\S]*?z-index:\s*(\d+);/)?.[1]);
  const modalOverlayZ = Number(css.match(/\.modal-overlay\s*\{[\s\S]*?z-index:\s*(\d+);/)?.[1]);

  assert.ok(Number.isFinite(stickyHeaderZ), "sticky table header z-index should be explicit");
  assert.ok(Number.isFinite(modalOverlayZ), "modal overlay z-index should be explicit");
  assert.ok(modalOverlayZ > stickyHeaderZ);
});
