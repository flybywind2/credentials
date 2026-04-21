import test from "node:test";
import assert from "node:assert/strict";

import {
  EMPLOYEE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  clearEmployeeId,
  loginWithEmployeeId,
} from "../js/auth.js";

test("loginWithEmployeeId stores access token and employee id", async () => {
  const storedValues = {};
  const previousStorage = globalThis.localStorage;
  const previousFetch = globalThis.fetch;
  globalThis.localStorage = {
    getItem: (key) => storedValues[key] || "",
    setItem: (key, value) => {
      storedValues[key] = value;
    },
    removeItem: (key) => {
      delete storedValues[key];
    },
  };
  globalThis.fetch = async (_path, options) => {
    assert.equal(JSON.parse(options.body).password, "secret");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: "signed-token",
        user: { employee_id: "part001", role: "INPUTTER" },
      }),
    };
  };

  try {
    const user = await loginWithEmployeeId("part001", "secret");

    assert.equal(user.employee_id, "part001");
    assert.equal(storedValues[EMPLOYEE_STORAGE_KEY], "part001");
    assert.equal(storedValues[TOKEN_STORAGE_KEY], "signed-token");

    clearEmployeeId();
    assert.equal(storedValues[EMPLOYEE_STORAGE_KEY], undefined);
    assert.equal(storedValues[TOKEN_STORAGE_KEY], undefined);
  } finally {
    globalThis.fetch = previousFetch;
    globalThis.localStorage = previousStorage;
  }
});
