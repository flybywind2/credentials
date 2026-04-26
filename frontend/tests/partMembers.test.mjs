import test from "node:test";
import assert from "node:assert/strict";

import { loadReadablePartMembers } from "../js/partMembers.js";

test("loadReadablePartMembers returns an empty list when part-member access is forbidden", async () => {
  const fetcher = async () => {
    const error = new Error("Insufficient permissions");
    error.status = 403;
    throw error;
  };

  const members = await loadReadablePartMembers(fetcher, 3);

  assert.deepEqual(members, []);
});

test("loadReadablePartMembers keeps non-permission errors visible", async () => {
  const fetcher = async () => {
    const error = new Error("Server failed");
    error.status = 500;
    throw error;
  };

  await assert.rejects(
    () => loadReadablePartMembers(fetcher, 3),
    /Server failed/,
  );
});

test("loadReadablePartMembers requests the selected organization when provided", async () => {
  let capturedPath = "";
  const fetcher = async (path) => {
    capturedPath = path;
    return [{ name: "홍길동" }];
  };

  const members = await loadReadablePartMembers(fetcher, 7);

  assert.equal(capturedPath, "/api/part-members?org_id=7");
  assert.deepEqual(members, [{ name: "홍길동" }]);
});
