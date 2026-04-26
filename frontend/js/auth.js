import { fetchJson } from "./api.js?v=20260426-mock-cookie";

export const EMPLOYEE_STORAGE_KEY = "credential_employee_id";
export const TOKEN_STORAGE_KEY = "credential_access_token";

function storageValue(storage, key) {
  try {
    return storage?.getItem(key) || "";
  } catch {
    return "";
  }
}

function setStorageValue(storage, key, value) {
  try {
    storage?.setItem(key, value);
  } catch {
    // Ignore storage failures; API calls can still pass explicit headers.
  }
}

function removeStorageValue(storage, key) {
  try {
    storage?.removeItem(key);
  } catch {
    // Ignore storage failures.
  }
}

export function savedEmployeeId() {
  return storageValue(globalThis.sessionStorage, EMPLOYEE_STORAGE_KEY)
    || storageValue(globalThis.localStorage, EMPLOYEE_STORAGE_KEY);
}

export function savedAccessToken() {
  return storageValue(globalThis.sessionStorage, TOKEN_STORAGE_KEY)
    || storageValue(globalThis.localStorage, TOKEN_STORAGE_KEY);
}

export function saveEmployeeId(employeeId) {
  setStorageValue(globalThis.sessionStorage, EMPLOYEE_STORAGE_KEY, employeeId);
  setStorageValue(globalThis.localStorage, EMPLOYEE_STORAGE_KEY, employeeId);
}

export function saveAccessToken(accessToken) {
  setStorageValue(globalThis.sessionStorage, TOKEN_STORAGE_KEY, accessToken);
  setStorageValue(globalThis.localStorage, TOKEN_STORAGE_KEY, accessToken);
}

export function clearEmployeeId() {
  removeStorageValue(globalThis.sessionStorage, EMPLOYEE_STORAGE_KEY);
  removeStorageValue(globalThis.sessionStorage, TOKEN_STORAGE_KEY);
  removeStorageValue(globalThis.localStorage, EMPLOYEE_STORAGE_KEY);
  removeStorageValue(globalThis.localStorage, TOKEN_STORAGE_KEY);
}

export async function logoutCurrentUser() {
  try {
    await fetchJson("/api/auth/logout", { method: "POST" });
  } catch {
    // Local logout should still clear the browser state if the server is unreachable.
  }
  clearEmployeeId();
}

export async function loginWithEmployeeId(employeeId, password = "") {
  const body = { employee_id: employeeId };
  if (password) {
    body.password = password;
  }
  const result = await fetchJson("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "X-Employee-Id": employeeId },
  });
  saveEmployeeId(result.user?.employee_id || employeeId);
  saveAccessToken(result.access_token);
  return result.user;
}

export async function loadCurrentUser() {
  const employeeId = savedEmployeeId();
  const accessToken = savedAccessToken();
  if (!employeeId && !accessToken) {
    try {
      const brokerUser = await fetchJson("/api/auth/me");
      return brokerUser?.sso_provider === "broker" ? brokerUser : null;
    } catch (error) {
      if (error.status === 401) {
        return null;
      }
      throw error;
    }
  }
  return fetchJson("/api/auth/me");
}
