import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { normalizeInputExampleRows } from "../js/inputExampleAdmin.js";

const source = readFileSync(new URL("../js/inputExampleAdmin.js", import.meta.url), "utf8");

test("normalizeInputExampleRows keeps editable example fields and removes blank rows", () => {
  assert.deepEqual(
    normalizeInputExampleRows([
      { major_task: "  예시 대업무  ", detail_task: "예시 세부업무", is_confidential: true },
      { major_task: "", detail_task: "", sub_part: "" },
    ]),
    [
      {
        sub_part: "",
        major_task: "예시 대업무",
        detail_task: "예시 세부업무",
        is_confidential: true,
        is_national_tech: false,
        is_compliance: false,
        storage_location: "",
        related_menu: "",
        share_scope: "",
      },
    ],
  );
});

test("input example admin manager uses admin input example APIs", () => {
  assert.match(source, /\/api\/admin\/input-examples/);
  assert.match(source, /입력 예시 데이터/);
  assert.match(source, /BOOLEAN_FIELDS/);
  assert.match(source, /"is_confidential"/);
  assert.match(source, /data-action="add-example-row"/);
  assert.match(source, /data-action="save-example-rows"/);
});
