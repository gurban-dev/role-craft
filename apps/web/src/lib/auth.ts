import { apiGet, apiPost, ApiError } from "./api";
import type { User } from "./types";

export async function getCurrentUser(): Promise<User | null> {
  try {
    return await apiGet<User>("/api/auth/me");
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      return null;
    }
    throw err;
  }
}

export async function loginRequest(email: string, password: string) {
  return apiPost<User>("/api/auth/login", { email, password });
}

export async function registerRequest(
  email: string,
  password: string,
  name: string,
) {
  return apiPost<User>("/api/auth/register", { email, password, name });
}

export async function logoutRequest() {
  return apiPost<void>("/api/auth/logout");
}
