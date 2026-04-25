import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import * as groupReadonly from "../js/groupReadonly.js";

const source = readFileSync(new URL("../js/groupReadonly.js", import.meta.url), "utf8");

test("group readonly rows keep absolute row numbers when paginated", () => {
  assert.equal(typeof groupReadonly.renderGroupRows, "function");

  const html = groupReadonly.renderGroupRows([
    {
      part_name: "파트A",
      sub_part: "소파트",
      major_task: "대업무",
      detail_task: "세부업무",
      status: "DRAFT",
    },
  ], 20);

  assert.match(html, /<td>21<\/td>/);
});

test("group readonly view renders pagination controls", () => {
  assert.match(source, /paginateItems/);
  assert.match(source, /renderPaginationControls/);
  assert.match(source, /data-group-pagination/);
  assert.match(source, /renderPaginationControls\(page,\s*"group-readonly"\)/);
});
