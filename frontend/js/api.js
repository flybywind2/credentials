export const ACCESS_TOKEN_STORAGE_KEY = "credential_access_token";
export const EMPLOYEE_STORAGE_KEY = "credential_employee_id";

function storageValue(storage, key) {
  try {
    return storage?.getItem(key) || "";
  } catch {
    return "";
  }
}

export function currentEmployeeId() {
  return storageValue(globalThis.sessionStorage, EMPLOYEE_STORAGE_KEY)
    || storageValue(globalThis.localStorage, EMPLOYEE_STORAGE_KEY);
}

export function currentAccessToken() {
  return storageValue(globalThis.sessionStorage, ACCESS_TOKEN_STORAGE_KEY)
    || storageValue(globalThis.localStorage, ACCESS_TOKEN_STORAGE_KEY);
}

export async function fetchJson(path, options = {}) {
  const employeeId = currentEmployeeId();
  const accessToken = currentAccessToken();
  const { headers: optionHeaders = {}, ...requestOptions } = options;
  let response;
  try {
    response = await fetch(path, {
      ...requestOptions,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(employeeId ? { "X-Employee-Id": employeeId } : {}),
        ...optionHeaders,
      },
    });
  } catch (error) {
    throw new Error(
      `API 서버에 연결할 수 없습니다. 브라우저는 http://127.0.0.1:8000/ 에서 열고 서버 실행 상태를 확인하세요. (${path})`,
    );
  }
  if (!response.ok) {
    let errorBody = null;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = null;
    }
    const detail = errorBody?.detail;
    const message = typeof detail === "object" && detail?.message
      ? detail.message
      : typeof detail === "string" && detail
        ? detail
      : `${path} 요청 실패: ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    if (Array.isArray(errorBody?.validation_errors)) {
      error.validationErrors = errorBody.validation_errors;
    }
    if (typeof detail === "object" && detail?.code) {
      error.code = detail.code;
      error.detail = detail;
    }
    throw error;
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}
