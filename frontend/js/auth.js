import { fetchJson } from "./api.js";

export async function loadCurrentUser() {
  return fetchJson("/api/auth/me");
}
