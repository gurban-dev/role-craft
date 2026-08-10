import { z } from "zod";
import type { ApiErrorBody } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export const CSRF_COOKIE = "jaa_csrf";
export const CSRF_HEADER = "X-CSRF-Token";

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody | null;

  constructor(message: string, status: number, body: ApiErrorBody | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function messageFromBody(body: ApiErrorBody | null, fallback: string): string {
  if (!body) return fallback;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => d.msg).filter(Boolean).join("; ") || fallback;
  }
  if (body.message) return body.message;
  return fallback;
}

type FetchOptions = {
  method?: string;
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
  /** When true, do not throw on non-2xx; return null for 404. */
  allowNotFound?: boolean;
};

async function parseJsonSafe(res: Response): Promise<ApiErrorBody | null> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as ApiErrorBody;
  } catch {
    return { message: text };
  }
}

function readBrowserCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const parts = document.cookie.split("; ");
  for (const part of parts) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    const key = part.slice(0, eq);
    if (key === name) {
      return decodeURIComponent(part.slice(eq + 1));
    }
  }
  return undefined;
}

/** Read CSRF token from the non-HttpOnly `jaa_csrf` cookie (browser or RSC). */
export async function getCsrfToken(): Promise<string | undefined> {
  const fromBrowser = readBrowserCookie(CSRF_COOKIE);
  if (fromBrowser) return fromBrowser;

  if (typeof window === "undefined") {
    try {
      const { cookies } = await import("next/headers");
      const jar = await cookies();
      return jar.get(CSRF_COOKIE)?.value;
    } catch {
      return undefined;
    }
  }
  return undefined;
}

async function serverCookieHeader(): Promise<string | undefined> {
  if (typeof window !== "undefined") return undefined;
  try {
    const { cookies } = await import("next/headers");
    const jar = await cookies();
    const all = jar.getAll();
    if (!all.length) return undefined;
    return all.map((c) => `${c.name}=${c.value}`).join("; ");
  } catch {
    return undefined;
  }
}

function isMutatingMethod(method: string): boolean {
  return !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const method = (options.method ?? (options.body !== undefined ? "POST" : "GET")).toUpperCase();
  const url = path.startsWith("http") ? path : `${API_URL}${path}`;
  const headers = new Headers(options.headers);

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (isMutatingMethod(method) && !headers.has(CSRF_HEADER)) {
    const csrf = await getCsrfToken();
    if (csrf) {
      headers.set(CSRF_HEADER, csrf);
    }
  }

  const cookieHeader = await serverCookieHeader();
  if (cookieHeader && !headers.has("Cookie")) {
    headers.set("Cookie", cookieHeader);
  }

  const res = await fetch(url, {
    method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    credentials: "include",
    signal: options.signal,
    cache: "no-store",
  });

  if (res.status === 204) {
    return undefined as T;
  }

  if (!res.ok) {
    if (options.allowNotFound && res.status === 404) {
      return null as T;
    }
    const body = await parseJsonSafe(res);
    throw new ApiError(
      messageFromBody(body, `Request failed (${res.status})`),
      res.status,
      body,
    );
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function apiGet<T>(path: string, options?: Omit<FetchOptions, "method" | "body">) {
  return apiFetch<T>(path, { ...options, method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown, options?: Omit<FetchOptions, "method" | "body">) {
  return apiFetch<T>(path, { ...options, method: "POST", body });
}

export function apiPut<T>(path: string, body?: unknown, options?: Omit<FetchOptions, "method" | "body">) {
  return apiFetch<T>(path, { ...options, method: "PUT", body });
}

/** Parse unknown JSON with a Zod schema; throws ApiError-friendly message on failure. */
export function parseWithSchema<T>(schema: z.ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new Error(result.error.issues.map((i) => i.message).join("; "));
  }
  return result.data;
}
