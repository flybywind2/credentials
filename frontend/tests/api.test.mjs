import test from "node:test";
import assert from "node:assert/strict";

import { fetchJson } from "../js/api.js";

function stubStorage(values) {
  const previousStorage = globalThis.localStorage;
  globalThis.localStorage = {
    getItem: (key) => values[key] || "",
  };
  return () => {
    globalThis.localStorage = previousStorage;
  };
}

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

test("fetchJson sends saved bearer token on API requests", async () => {
  const restoreStorage = stubStorage({
    credential_access_token: "signed-token",
    credential_employee_id: "part001",
  });
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
    await fetchJson("/api/tasks");
  } finally {
    globalThis.fetch = previousFetch;
    restoreStorage();
  }

  assert.equal(capturedOptions.headers.Authorization, "Bearer signed-token");
  assert.equal(capturedOptions.headers["X-Employee-Id"], "part001");
});

test("fetchJson explains network failures with single-port guidance", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  try {
    await assert.rejects(
      () => fetchJson("/api/auth/login"),
      /API 서버에 연결할 수 없습니다.*http:\/\/127\.0\.0\.1:8000\//,
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});
