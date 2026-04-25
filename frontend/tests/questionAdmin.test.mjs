import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { moveQuestionId, normalizeQuestionOptions } from "../js/questionAdmin.js";

const questionAdminSource = readFileSync(new URL("../js/questionAdmin.js", import.meta.url), "utf8");

test("normalizeQuestionOptions always returns the fixed positive classification option", () => {
  const options = normalizeQuestionOptions(" 해당 없음, 설계 자료\n공정 조건;설계 자료 ");

  assert.deepEqual(options, ["해당 됨"]);
});

test("question manager explains fixed classification choices", () => {
  assert.match(questionAdminSource, /선택지는 “해당 없음”과 “해당 됨”으로 고정됩니다\./);
  assert.doesNotMatch(questionAdminSource, /name="options"/);
});

test("moveQuestionId moves ids up and down without leaving bounds", () => {
  assert.deepEqual(moveQuestionId([1, 2, 3], 2, "up"), [2, 1, 3]);
  assert.deepEqual(moveQuestionId([1, 2, 3], 2, "down"), [1, 3, 2]);
  assert.deepEqual(moveQuestionId([1, 2, 3], 1, "up"), [1, 2, 3]);
  assert.deepEqual(moveQuestionId([1, 2, 3], 3, "down"), [1, 2, 3]);
});

test("question manager exposes tabs and drag-and-drop reorder", () => {
  assert.match(questionAdminSource, /role="tablist"/);
  assert.match(questionAdminSource, /draggable="true"/);
  assert.match(questionAdminSource, /dragstart/);
  assert.match(questionAdminSource, /drop/);
});
