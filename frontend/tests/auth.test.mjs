import test from "node:test";
import assert from "node:assert/strict";

import {
  EMPLOYEE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  clearEmployeeId,
  brokerCallbackParams,
  exchangeBrokerCallback,
  loginWithEmployeeId,
  logoutCurrentUser,
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

test("logoutCurrentUser clears storage and server mock cookie", async () => {
  const localValues = {
    [EMPLOYEE_STORAGE_KEY]: "group001",
    [TOKEN_STORAGE_KEY]: "signed-token",
  };
  const sessionValues = {
    [EMPLOYEE_STORAGE_KEY]: "group001",
    [TOKEN_STORAGE_KEY]: "signed-token",
  };
  const previousLocalStorage = globalThis.localStorage;
  const previousSessionStorage = globalThis.sessionStorage;
  const previousFetch = globalThis.fetch;
  let capturedPath = "";
  let capturedOptions = null;

  globalThis.localStorage = {
    getItem: (key) => localValues[key] || "",
    removeItem: (key) => {
      delete localValues[key];
    },
  };
  globalThis.sessionStorage = {
    getItem: (key) => sessionValues[key] || "",
    removeItem: (key) => {
      delete sessionValues[key];
    },
  };
  globalThis.fetch = async (path, options) => {
    capturedPath = path;
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    };
  };

  try {
    await logoutCurrentUser();

    assert.equal(capturedPath, "/api/auth/logout");
    assert.equal(capturedOptions.method, "POST");
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

test("brokerCallbackParams reads broker redirect query values", () => {
  const params = brokerCallbackParams("?loginid=group001&deptname=AI%2FIT%EC%A0%84%EB%9E%B5%EA%B7%B8%EB%A3%B9&username=%EB%B0%95%EB%AF%BC%EC%9E%AC");

  assert.deepEqual(params, {
    loginid: "group001",
    deptname: "AI/IT전략그룹",
    username: "박민재",
  });
});

test("exchangeBrokerCallback posts broker query values to the session endpoint", async () => {
  const previousFetch = globalThis.fetch;
  let capturedPath = "";
  let capturedOptions = null;
  globalThis.fetch = async (path, options) => {
    capturedPath = path;
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      json: async () => ({ user: { employee_id: "group001", role: "APPROVER" } }),
    };
  };

  try {
    const user = await exchangeBrokerCallback({
      loginid: "group001",
      deptname: "AI/IT전략그룹",
      username: "박민재",
    });

    assert.equal(capturedPath, "/api/auth/broker/session");
    assert.equal(capturedOptions.method, "POST");
    assert.deepEqual(JSON.parse(capturedOptions.body), {
      loginid: "group001",
      deptname: "AI/IT전략그룹",
      username: "박민재",
    });
    assert.equal(user.employee_id, "group001");
  } finally {
    globalThis.fetch = previousFetch;
  }
});
