import test from "node:test";
import assert from "node:assert/strict";

import { fetchJson } from "../js/api.js";

function stubStorage(localValues, sessionValues = {}) {
  const previousLocalStorage = globalThis.localStorage;
  const previousSessionStorage = globalThis.sessionStorage;
  globalThis.localStorage = {
    getItem: (key) => localValues[key] || "",
  };
  globalThis.sessionStorage = {
    getItem: (key) => sessionValues[key] || "",
  };
  return () => {
    globalThis.localStorage = previousLocalStorage;
    globalThis.sessionStorage = previousSessionStorage;
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

test("fetchJson prefers the current window mock user over shared local storage", async () => {
  const restoreStorage = stubStorage(
    {
      credential_access_token: "admin-token",
      credential_employee_id: "admin001",
    },
    {
      credential_access_token: "group-token",
      credential_employee_id: "group001",
    },
  );
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
    await fetchJson("/api/approvals/subordinate-status");
  } finally {
    globalThis.fetch = previousFetch;
    restoreStorage();
  }

  assert.equal(capturedOptions.headers.Authorization, "Bearer group-token");
  assert.equal(capturedOptions.headers["X-Employee-Id"], "group001");
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

test("fetchJson preserves structured organization mapping errors", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({
      detail: {
        code: "ORG_MAPPING_REQUIRED",
        message: "소속에 맞는 파트 정보가 없습니다. 담당자에게 정보 등록을 요청해 주세요.",
      },
    }),
  });

  try {
    await assert.rejects(
      () => fetchJson("/api/auth/me"),
      (error) => {
        assert.equal(error.status, 409);
        assert.equal(error.code, "ORG_MAPPING_REQUIRED");
        assert.match(error.message, /담당자에게 정보 등록/);
        return true;
      },
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});
