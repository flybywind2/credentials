export const ACCESS_TOKEN_STORAGE_KEY = "credential_access_token";

export function currentEmployeeId() {
  try {
    return globalThis.localStorage?.getItem("credential_employee_id") || "";
  } catch {
    return "";
  }
}

export function currentAccessToken() {
  try {
    return globalThis.localStorage?.getItem(ACCESS_TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export async function fetchJson(path, options = {}) {
  const employeeId = currentEmployeeId();
  const accessToken = currentAccessToken();
  const { headers: optionHeaders = {}, ...requestOptions } = options;
  const response = await fetch(path, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(employeeId ? { "X-Employee-Id": employeeId } : {}),
      ...optionHeaders,
    },
  });
  if (!response.ok) {
    throw new Error(`${path} 요청 실패: ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}
