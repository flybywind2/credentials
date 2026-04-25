import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const partStatusSource = readFileSync(new URL("../js/partStatus.js", import.meta.url), "utf8");

test("part status page renders part members as a read-only list", () => {
  assert.match(partStatusSource, /\/api\/part-members/);
  assert.match(partStatusSource, /파트원 명단/);
  assert.doesNotMatch(partStatusSource, /\/api\/part-members\/import/);
  assert.doesNotMatch(partStatusSource, /type="file"/);
  assert.doesNotMatch(partStatusSource, /text\/csv/);
});
