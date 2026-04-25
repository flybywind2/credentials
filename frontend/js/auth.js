import { fetchJson } from "./api.js";

export const EMPLOYEE_STORAGE_KEY = "credential_employee_id";
export const TOKEN_STORAGE_KEY = "credential_access_token";

export function savedEmployeeId() {
  try {
    return globalThis.localStorage?.getItem(EMPLOYEE_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function savedAccessToken() {
  try {
    return globalThis.localStorage?.getItem(TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function saveEmployeeId(employeeId) {
  try {
    globalThis.localStorage?.setItem(EMPLOYEE_STORAGE_KEY, employeeId);
  } catch {
    // Ignore storage failures; API calls can still pass explicit headers.
  }
}

export function saveAccessToken(accessToken) {
  try {
    globalThis.localStorage?.setItem(TOKEN_STORAGE_KEY, accessToken);
  } catch {
    // Ignore storage failures; the current page can still use explicit responses.
  }
}

export function clearEmployeeId() {
  try {
    globalThis.localStorage?.removeItem(EMPLOYEE_STORAGE_KEY);
    globalThis.localStorage?.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
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
  saveEmployeeId(employeeId);
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
