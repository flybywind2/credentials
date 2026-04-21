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
    throw new Error(`${path} 요청 실패: ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}
