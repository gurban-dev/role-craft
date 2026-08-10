import { afterEach, describe, expect, it, vi } from "vitest";
import { API_URL, CSRF_COOKIE, CSRF_HEADER, apiGet, apiPost } from "@/lib/api";

describe("apiFetch CSRF", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = `${CSRF_COOKIE}=; Max-Age=0; path=/`;
  });

  it("sends X-CSRF-Token from jaa_csrf cookie on mutating requests", async () => {
    document.cookie = `${CSRF_COOKIE}=csrf-test-token; path=/`;

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiPost("/api/applications/1/approve", {});

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_URL}/api/applications/1/approve`,
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init).toBeDefined();
    const headers = new Headers(init!.headers);
    expect(headers.get(CSRF_HEADER)).toBe("csrf-test-token");
  });

  it("does not require CSRF header on GET", async () => {
    document.cookie = `${CSRF_COOKIE}=csrf-test-token; path=/`;

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiGet("/api/health");

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init).toBeDefined();
    const headers = new Headers(init!.headers);
    expect(headers.get(CSRF_HEADER)).toBeNull();
  });
});
