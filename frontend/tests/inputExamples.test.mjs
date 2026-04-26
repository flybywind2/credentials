import test from "node:test";
import assert from "node:assert/strict";

import {
  EXAMPLE_DATA_STORAGE_KEY,
  isExampleDataVisible,
  renderInputExamplePanel,
  setExampleDataVisible,
} from "../js/inputExamples.js";

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

test("example data visibility is stored in localStorage", () => {
  const storage = memoryStorage();

  assert.equal(isExampleDataVisible(storage), false);
  setExampleDataVisible(true, storage);
  assert.equal(storage.getItem(EXAMPLE_DATA_STORAGE_KEY), "true");
  assert.equal(isExampleDataVisible(storage), true);
  setExampleDataVisible(false, storage);
  assert.equal(isExampleDataVisible(storage), false);
});

test("renderInputExamplePanel renders a read-only example task table", () => {
  const html = renderInputExamplePanel([
    {
      sub_part: "예시파트",
      major_task: "예시 대업무",
      detail_task: "예시 세부업무",
      is_confidential: true,
      is_national_tech: false,
      is_compliance: true,
    },
  ]);

  assert.match(html, /예시 데이터/);
  assert.match(html, /예시 대업무/);
  assert.match(html, /기밀/);
  assert.match(html, /Compliance/);
});
