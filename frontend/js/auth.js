import { fetchJson } from "./api.js";

export const EMPLOYEE_STORAGE_KEY = "credential_employee_id";

export function savedEmployeeId() {
  try {
    return globalThis.localStorage?.getItem(EMPLOYEE_STORAGE_KEY) || "";
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

export function clearEmployeeId() {
  try {
    globalThis.localStorage?.removeItem(EMPLOYEE_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
}

export async function loginWithEmployeeId(employeeId) {
  const result = await fetchJson("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId }),
    headers: { "X-Employee-Id": employeeId },
  });
  saveEmployeeId(employeeId);
  return result.user;
}

export async function loadCurrentUser() {
  const employeeId = savedEmployeeId();
  if (!employeeId) {
    return null;
  }
  return fetchJson("/api/auth/me");
}
