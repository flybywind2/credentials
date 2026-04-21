import test from "node:test";
import assert from "node:assert/strict";

import { moveQuestionId, normalizeQuestionOptions } from "../js/questionAdmin.js";

test("normalizeQuestionOptions trims, deduplicates, and omits none option", () => {
  const options = normalizeQuestionOptions(" 해당 없음, 설계 자료\n공정 조건;설계 자료 ");

  assert.deepEqual(options, ["설계 자료", "공정 조건"]);
});

test("normalizeQuestionOptions returns an empty list for blank option text", () => {
  assert.deepEqual(normalizeQuestionOptions(" \n, ; "), []);
});

test("moveQuestionId moves ids up and down without leaving bounds", () => {
  assert.deepEqual(moveQuestionId([1, 2, 3], 2, "up"), [2, 1, 3]);
  assert.deepEqual(moveQuestionId([1, 2, 3], 2, "down"), [1, 3, 2]);
  assert.deepEqual(moveQuestionId([1, 2, 3], 1, "up"), [1, 2, 3]);
  assert.deepEqual(moveQuestionId([1, 2, 3], 3, "down"), [1, 2, 3]);
});
