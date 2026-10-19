import { afterEach, describe, expect, it, vi } from "vitest";
import { proxyRequest, proxySettings, type ProxySettings } from "../src/server/staging-proxy";
import { defaultPlan, universities, scholarships } from "../src/data/staging-demo";

const settings: ProxySettings = { frontend: "https://demo-web.onrender.com", upstream: "https://demo-api.onrender.com", key: "K".repeat(43) };
const token = "A".repeat(43);
const issued = `atlas_session=${token}; Path=/; Secure; HttpOnly; SameSite=Lax`;
function request(path = "/api/v1/auth/login", method = "POST", headers: Record<string, string> = {}, body: BodyInit | undefined = "{}") {
  return new Request(settings.frontend + path, { method, headers: { Host: "demo-web.onrender.com", Origin: settings.frontend, "X-Atlas-CSRF": "synthetic-csrf", "Content-Type": "application/json", ...headers }, body: method === "GET" ? undefined : body, duplex: "half" } as RequestInit);
}
const json = () => Response.json({ ok: true });
const badContexts: Record<string, string>[] = [
  { Host: "evil.invalid" }, { Origin: "https://evil.invalid" }, { Origin: "" },
  { "X-Atlas-CSRF": "" }, { Referer: "https://evil.invalid/" }, { Referer: "not a URL" },
  { "Sec-Fetch-Site": "cross-site" },
];
afterEach(() => vi.unstubAllEnvs());

describe("same-origin demo transport", () => {
  it("fails closed unless explicitly configured", async () => {
    expect(proxySettings({})).toBeNull();
    const fetcher = vi.fn<typeof fetch>();
    expect((await proxyRequest(request(), null, fetcher)).status).toBe(503);
    expect(fetcher).not.toHaveBeenCalled();
  });
  const env = { ATLAS_STAGING_PROXY_ENABLED: "true", ATLAS_STAGING_TRANSPORT_KEY: settings.key, ATLAS_STAGING_FRONTEND_ORIGIN: settings.frontend, ATLAS_STAGING_BACKEND_ORIGIN: settings.upstream };
  it.each(["http://demo-api.onrender.com", "https://user:password@demo-api.onrender.com", "https://demo-api.onrender.com/path", "https://demo-api.onrender.com?upstream=evil", "https://demo-api.onrender.com#fragment", "https://other.invalid", "https://demo-api.onrender.com:1234", settings.frontend])("rejects unsafe upstream %s", upstream => {
    expect(() => proxySettings({ ...env, ATLAS_STAGING_BACKEND_ORIGIN: upstream })).toThrow();
  });
  it("accepts only server-owned exact origins and a bounded key", () => {
    expect(proxySettings(env)).toEqual(settings);
    expect(() => proxySettings({ ...env, ATLAS_STAGING_TRANSPORT_KEY: "short" })).toThrow();
  });
  it.each([
    ["GET", "/api/v1/auth/me"], ["POST", "/api/v1/auth/login"],
    ["PUT", "/api/v1/me/comparison"], ["PATCH", "/api/v1/me/profile"],
    ["DELETE", "/api/v1/me/universities/fictional"], ["GET", "/api/v2/scholarships"],
  ])("forwards %s %s with original CSRF/Origin", async (method, path) => {
    const fake = vi.fn<typeof fetch>(async (url, init) => {
      expect(String(url)).toBe(settings.upstream + path);
      expect(init?.method).toBe(method);
      const headers = new Headers(init?.headers);
      expect(headers.get("Origin")).toBe(settings.frontend);
      expect(headers.get("X-Atlas-CSRF")).toBe("synthetic-csrf");
      expect(headers.get("X-Atlas-Staging-Key")).toBe(settings.key);
      expect(init?.cache).toBe("no-store"); expect(init?.redirect).toBe("manual");
      return json();
    });
    const response = await proxyRequest(request(path, method), settings, fake);
    expect(response.status).toBe(200); expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(fake).toHaveBeenCalledTimes(1);
  });
  it.each(["/api/v1/staging-mail/consume", "/api/v1/me/import", "/api/v1/me/export", "/api/v1/advisor/ask", "/api/v1/https://evil.invalid", "/api/v2/unknown"])("does not expose %s", async path => {
    const fake = vi.fn<typeof fetch>();
    expect((await proxyRequest(request(path), settings, fake)).status).toBe(404);
    expect(fake).not.toHaveBeenCalled();
  });
  it.each(badContexts)("rejects untrusted browser context %j", async headers => {
    const fake = vi.fn<typeof fetch>();
    expect((await proxyRequest(request(undefined, undefined, headers), settings, fake)).status).toBe(403);
    expect(fake).not.toHaveBeenCalled();
  });
  it("does not forward spoofed identity, authorization, proxy key or unrelated cookies", async () => {
    const fake = vi.fn<typeof fetch>(async (_, init) => {
      const h = new Headers(init?.headers);
      for (const name of ["Host", "X-Forwarded-For", "X-Forwarded-Host", "Authorization", "X-Atlas-Mailbox-Key"]) expect(h.has(name)).toBe(false);
      expect(h.get("X-Atlas-Staging-Key")).toBe(settings.key);
      expect(h.get("Cookie")).toBe(`atlas_session=${token}`);
      return json();
    });
    await proxyRequest(request(undefined, undefined, { "X-Forwarded-For": "spoofed", "X-Forwarded-Host": "evil.invalid", Authorization: "private", "X-Atlas-Staging-Key": "forged", "X-Atlas-Mailbox-Key": "private", Cookie: `other=private; atlas_session=${token}` }), settings, fake);
    expect(fake).toHaveBeenCalledOnce();
  });
  it("preserves separate creation/deletion Set-Cookie headers and Expires commas", async () => {
    const headers = new Headers({ "Content-Type": "application/json" });
    headers.append("Set-Cookie", issued);
    headers.append("Set-Cookie", 'atlas_session=""; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; HttpOnly; SameSite=Lax');
    const response = await proxyRequest(request("/api/v1/auth/logout"), settings, async () => new Response("{}", { headers }));
    expect(response.headers.getSetCookie()).toEqual(headers.getSetCookie());
  });
  it.each([issued + "; Domain=onrender.com", issued.replace("Secure; ", ""), issued.replace("HttpOnly; ", ""), issued.replace("Lax", "None"), issued.replace("Path=/;", "Path=/auth;"), issued + "; SameSite=None"])("rejects unsafe upstream cookies", async value => {
    expect((await proxyRequest(request(), settings, async () => Response.json({}, { headers: { "Set-Cookie": value } }))).status).toBe(503);
  });
  it("rejects duplicate session cookies", async () => {
    expect((await proxyRequest(request(undefined, undefined, { Cookie: `atlas_session=${token}; atlas_session=${token}` }), settings, async () => json())).status).toBe(400);
  });
  it("bounds body size and content type before forwarding", async () => {
    const fake = vi.fn<typeof fetch>();
    expect((await proxyRequest(request(undefined, undefined, {}, "x".repeat(65537)), settings, fake)).status).toBe(413);
    expect((await proxyRequest(request(undefined, undefined, { "Content-Type": "text/plain" }), settings, fake)).status).toBe(415);
    expect(fake).not.toHaveBeenCalled();
  });
  it("bounds a stalled incoming stream", async () => {
    const fake = vi.fn<typeof fetch>();
    const response = await proxyRequest(request(undefined, undefined, {}, new ReadableStream()), settings, fake, 10);
    expect(response.status).toBe(503); expect(fake).not.toHaveBeenCalled();
  });
  it("bounds a stalled response stream", async () => {
    const response = await proxyRequest(request(), settings, async () => new Response(new ReadableStream(), { headers: { "Content-Type": "application/json" } }), 10);
    expect(response.status).toBe(503);
  });
  it("bounds oversized responses", async () => {
    expect((await proxyRequest(request(), settings, async () => new Response("x".repeat(2 * 1024 * 1024 + 1), { headers: { "Content-Type": "application/json" } }))).status).toBe(503);
  });
  it("rejects redirects and Render HTML warmup pages", async () => {
    const redirected = await proxyRequest(request(), settings, async () => new Response(null, { status: 302, headers: { Location: "https://evil.invalid" } }));
    expect(redirected.status).toBe(503); expect(redirected.headers.has("Location")).toBe(false);
    expect((await proxyRequest(request(), settings, async () => new Response("warming up", { headers: { "Content-Type": "text/html" } }))).status).toBe(503);
  });
  it("never retries uncertain POSTs and recovers on a later manual request", async () => {
    const fake = vi.fn<typeof fetch>().mockRejectedValueOnce(new Error("private sentinel")).mockImplementationOnce(async () => json());
    const unavailable = await proxyRequest(request(), settings, fake);
    expect(unavailable.status).toBe(503); expect(await unavailable.text()).not.toContain("private sentinel");
    expect(fake).toHaveBeenCalledTimes(1);
    expect((await proxyRequest(request(), settings, fake)).status).toBe(200);
    expect(fake).toHaveBeenCalledTimes(2);
  });
  it.each([401, 403, 422, 429])("preserves auth/validation status %i without internal headers", async status => {
    const result = await proxyRequest(request(), settings, async () => Response.json({ error: { message: "synthetic" } }, { status, headers: { "X-Internal": "private", "Retry-After": "60" } }));
    expect(result.status).toBe(status); expect(result.headers.has("X-Internal")).toBe(false);
    expect(result.headers.get("Retry-After")).toBe("60");
  });
  it("keeps concurrent request cookies and responses isolated", async () => {
    const fake: typeof fetch = async (_, init) => Response.json({ cookie: new Headers(init?.headers).get("Cookie") });
    const [a, b] = await Promise.all(["A", "B"].map(c => proxyRequest(request("/api/v1/auth/me", "GET", { Cookie: `atlas_session=${c.repeat(43)}` }), settings, fake)));
    expect((await a.json()).cookie).toBe(`atlas_session=${"A".repeat(43)}`);
    expect((await b.json()).cookie).toBe(`atlas_session=${"B".repeat(43)}`);
  });
  it("uses empty staging catalogs with no assumed scholarship deduction", () => {
    expect(universities).toEqual([]); expect(scholarships).toEqual([]);
    expect(defaultPlan.scholarship).toBe(0); expect(defaultPlan.university).toBe("");
    expect(defaultPlan.currency).toBe("CNY");
  });
});
