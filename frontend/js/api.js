export async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${path} 요청 실패: ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}
