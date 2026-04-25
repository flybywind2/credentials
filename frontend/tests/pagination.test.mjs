import test from "node:test";
import assert from "node:assert/strict";

import {
  PAGE_SIZE,
  clampPage,
  pageCount,
  paginateItems,
  paginationSummary,
} from "../js/pagination.js";

test("paginateItems returns a bounded page of rows", () => {
  const items = Array.from({ length: 45 }, (_, index) => index + 1);

  assert.equal(PAGE_SIZE, 20);
  assert.deepEqual(paginateItems(items, 1).items, items.slice(0, 20));
  assert.deepEqual(paginateItems(items, 3).items, items.slice(40, 45));
  assert.equal(paginateItems(items, 99).page, 3);
});

test("pagination helpers handle empty and partial pages", () => {
  assert.equal(pageCount(0), 1);
  assert.equal(pageCount(41), 3);
  assert.equal(clampPage(0, 41), 1);
  assert.equal(clampPage(9, 41), 3);
  assert.equal(paginationSummary({ total: 0, page: 1, pageSize: 20 }), "0 / 0");
  assert.equal(paginationSummary({ total: 41, page: 3, pageSize: 20 }), "41-41 / 41");
});
