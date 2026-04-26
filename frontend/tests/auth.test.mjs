import test from "node:test";
import assert from "node:assert/strict";

import {
  EMPLOYEE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  clearEmployeeId,
  loginWithEmployeeId,
} from "../js/auth.js";

test("loginWithEmployeeId stores access token and employee id", async () => {
  const localValues = {};
  const sessionValues = {};
  const previousLocalStorage = globalThis.localStorage;
  const previousSessionStorage = globalThis.sessionStorage;
  const previousFetch = globalThis.fetch;
  globalThis.localStorage = {
    getItem: (key) => localValues[key] || "",
    setItem: (key, value) => {
      localValues[key] = value;
    },
    removeItem: (key) => {
      delete localValues[key];
    },
  };
  globalThis.sessionStorage = {
    getItem: (key) => sessionValues[key] || "",
    setItem: (key, value) => {
      sessionValues[key] = value;
    },
    removeItem: (key) => {
      delete sessionValues[key];
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
    assert.equal(localValues[EMPLOYEE_STORAGE_KEY], "part001");
    assert.equal(localValues[TOKEN_STORAGE_KEY], "signed-token");
    assert.equal(sessionValues[EMPLOYEE_STORAGE_KEY], "part001");
    assert.equal(sessionValues[TOKEN_STORAGE_KEY], "signed-token");

    clearEmployeeId();
    assert.equal(localValues[EMPLOYEE_STORAGE_KEY], undefined);
    assert.equal(localValues[TOKEN_STORAGE_KEY], undefined);
    assert.equal(sessionValues[EMPLOYEE_STORAGE_KEY], undefined);
    assert.equal(sessionValues[TOKEN_STORAGE_KEY], undefined);
  } finally {
    globalThis.fetch = previousFetch;
    globalThis.localStorage = previousLocalStorage;
    globalThis.sessionStorage = previousSessionStorage;
  }
});
