import test from "node:test";
import assert from "node:assert/strict";

import { tooltipMap } from "../js/tooltipAdmin.js";

test("tooltipMap indexes tooltips by column key", () => {
  assert.deepEqual(
    tooltipMap([{ column_key: "major_task", example_text: "예시" }]),
    { major_task: "예시" },
  );
});
