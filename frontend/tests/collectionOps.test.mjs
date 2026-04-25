import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const dashboardSource = readFileSync(new URL("../js/dashboard.js", import.meta.url), "utf8");
const collectionOpsUrl = new URL("../js/collectionOps.js", import.meta.url);

test("admin dashboard mounts the one-time collection operations manager", () => {
  assert.match(dashboardSource, /renderCollectionOpsManager/);
  assert.match(dashboardSource, /collection-ops-root/);
});

test("collection operations manager exposes lock status, audit logs, and mail failures", () => {
  assert.equal(existsSync(collectionOpsUrl), true);
  const source = readFileSync(collectionOpsUrl, "utf8");

  assert.match(source, /\/api\/admin\/collection\/status/);
  assert.match(source, /\/api\/admin\/audit-logs/);
  assert.match(source, /collection_locked/);
  assert.match(source, /메일 발송 실패/);
  assert.match(source, /최종 Export/);
  assert.match(source, /감사 로그/);
});
