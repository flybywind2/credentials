import test from "node:test";
import assert from "node:assert/strict";

import { fetchJson } from "../js/api.js";

test("fetchJson keeps json content type when custom headers are passed", async () => {
  const previousFetch = globalThis.fetch;
  let capturedOptions = null;
  globalThis.fetch = async (_path, options) => {
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    };
  };

  try {
    await fetchJson("/api/auth/login", {
      method: "POST",
      headers: { "X-Employee-Id": "part001" },
      body: JSON.stringify({ employee_id: "part001" }),
    });
  } finally {
    globalThis.fetch = previousFetch;
  }

  assert.equal(capturedOptions.headers["Content-Type"], "application/json");
  assert.equal(capturedOptions.headers["X-Employee-Id"], "part001");
});
