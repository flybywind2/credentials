export function currentEmployeeId() {
  try {
    return globalThis.localStorage?.getItem("credential_employee_id") || "";
  } catch {
    return "";
  }
}

export async function fetchJson(path, options = {}) {
  const employeeId = currentEmployeeId();
  const { headers: optionHeaders = {}, ...requestOptions } = options;
  const response = await fetch(path, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
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
