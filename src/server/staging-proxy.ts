// Server Route Handlers only. FastAPI remains the session/CSRF authority.
export interface ProxySettings { frontend: string; upstream: string; key: string }
function renderOrigin(value: string | undefined): string {
  if (!value) throw new Error("Missing proxy origin");
  const u = new URL(value);
  if (u.protocol !== "https:" || u.username || u.password || u.port ||
    !/^[a-z0-9][a-z0-9-]*\.onrender\.com$/.test(u.hostname) ||
    u.pathname !== "/" || u.search || u.hash || value !== u.origin)
    throw new Error("An exact Render HTTPS origin is required");
  return u.origin;
}
export function proxySettings(env: Record<string, string | undefined>): ProxySettings | null {
  if (env.ATLAS_STAGING_PROXY_ENABLED !== "true") return null;
  const key = env.ATLAS_STAGING_TRANSPORT_KEY ?? "";
  if (!/^[A-Za-z0-9_-]{43,128}$/.test(key)) throw new Error("Missing proxy key");
  const frontend = renderOrigin(env.ATLAS_STAGING_FRONTEND_ORIGIN);
  const upstream = renderOrigin(env.ATLAS_STAGING_BACKEND_ORIGIN);
  if (frontend === upstream) throw new Error("Proxy origin loop");
  return { frontend, upstream, key };
}
const routes: [RegExp, string[]][] = [
  [/^\/api\/v1\/(health|ready|countries|catalog-options|financial-reference)$/, ["GET"]],
  [/^\/api\/v1\/(universities|scholarships)(\/[A-Za-z0-9_-]{1,120})?$/, ["GET"]],
  [/^\/api\/v1\/auth\/(register|login|logout|resend-verification|forgot-password|verify-email|reset-password)$/, ["POST"]],
  [/^\/api\/v1\/auth\/me$/, ["GET"]],
  [/^\/api\/v1\/auth\/sessions$/, ["GET", "DELETE"]],
  [/^\/api\/v1\/auth\/sessions\/[A-Za-z0-9-]{1,36}$/, ["DELETE"]],
  [/^\/api\/v1\/me\/(dashboard|workspace)$/, ["GET"]],
  [/^\/api\/v1\/me\/profile$/, ["GET", "PATCH"]],
  [/^\/api\/v1\/me\/(universities|scholarships|financial-plans)$/, ["GET", "POST"]],
  [/^\/api\/v1\/me\/(universities|scholarships)\/[A-Za-z0-9_-]{1,120}$/, ["DELETE"]],
  [/^\/api\/v1\/me\/financial-plans\/[A-Za-z0-9-]{1,36}$/, ["GET", "PATCH", "DELETE"]],
  [/^\/api\/v1\/me\/(comparison|checklists)$/, ["GET", "PUT"]],
  [/^\/api\/v1\/me\/financial-scenarios\/calculate$/, ["POST"]],
  [/^\/api\/v1\/me\/intelligence\/completeness$/, ["GET"]],
  [/^\/api\/v1\/me\/intelligence\/matches$/, ["POST"]],
  [/^\/api\/v1\/me\/intelligence\/assessments\/[A-Za-z0-9_-]{1,120}$/, ["POST"]],
  [/^\/api\/v2\/scholarships(\/[A-Za-z0-9_-]{1,120})?$/, ["GET"]],
  [/^\/api\/v2\/intelligence\/(universities|programs)(\/[A-Za-z0-9_-]{1,120})?$/, ["GET"]],
  [/^\/api\/v2\/intelligence\/compare\/(universities|programs)$/, ["GET"]],
];
function error(status: number, message: string) {
  return Response.json({ error: { message } }, { status, headers: {
    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
    ...(status === 503 ? { "Retry-After": "60" } : {}),
  } });
}
async function readBounded(stream: ReadableStream<Uint8Array> | null, limit: number, signal: AbortSignal) {
  if (!stream) return null;
  const reader = stream.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  let abort: () => void = () => {};
  const cancelled = new Promise<never>((_, reject) => {
    abort = () => reject(new Error("Transport deadline"));
    if (signal.aborted) abort(); else signal.addEventListener("abort", abort, { once: true });
  });
  try {
    while (true) {
      const chunk = await Promise.race([reader.read(), cancelled]);
      if (chunk.done) break;
      size += chunk.value.byteLength;
      if (size > limit) throw new RangeError("Payload limit");
      chunks.push(chunk.value);
    }
    const result = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
    return result;
  } catch (reason) {
    void reader.cancel().catch(() => {});
    throw reason;
  } finally { signal.removeEventListener("abort", abort); reader.releaseLock(); }
}
function safeCookie(value: string): boolean {
  const [pair, ...raw] = value.split(";").map(v => v.trim());
  if (!/^atlas_session=(?:[A-Za-z0-9_-]{40,100}|""|)$/.test(pair)) return false;
  const attributes = new Map<string, string>();
  for (const item of raw) {
    const i = item.indexOf("=");
    const name = (i < 0 ? item : item.slice(0, i)).toLowerCase();
    if (attributes.has(name) || !["path", "secure", "httponly", "samesite", "max-age", "expires"].includes(name)) return false;
    attributes.set(name, i < 0 ? "" : item.slice(i + 1));
  }
  return attributes.get("path") === "/" && attributes.get("samesite")?.toLowerCase() === "lax" &&
    attributes.get("secure") === "" && attributes.get("httponly") === "";
}
export async function proxyRequest(request: Request, settings: ProxySettings | null, fetcher: typeof fetch = fetch, timeoutMs = 10000): Promise<Response> {
  if (!settings) return error(503, "The demo API is not configured.");
  const url = new URL(request.url);
  // Bind Host, not Next's internal HTTP URL or any X-Forwarded-* value.
  if (request.headers.get("Host") !== new URL(settings.frontend).host) return error(403, "Untrusted demo host.");
  const methods = routes.find(([pattern]) => pattern.test(url.pathname))?.[1];
  if (!methods?.includes(request.method) || url.search.length > 2048) return error(404, "Demo API route unavailable.");
  const origin = request.headers.get("Origin");
  if ((origin && origin !== settings.frontend) || request.headers.get("Sec-Fetch-Site") === "cross-site") return error(403, "Untrusted request origin.");
  const referer = request.headers.get("Referer");
  if (referer) {
    try { if (new URL(referer).origin !== settings.frontend) return error(403, "Untrusted request referrer."); }
    catch { return error(403, "Invalid request referrer."); }
  }
  if (request.method !== "GET" && (origin !== settings.frontend || !request.headers.get("X-Atlas-CSRF"))) return error(403, "A trusted origin and CSRF header are required.");
  if (request.body && !/^application\/json(?:\s*;|$)/i.test(request.headers.get("Content-Type") ?? "")) return error(415, "JSON requests are required.");
  const headers = new Headers({ Accept: "application/json", "X-Atlas-Staging-Key": settings.key });
  for (const name of ["Content-Type", "Origin", "Referer", "X-Atlas-CSRF"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const cookies = (request.headers.get("Cookie") ?? "").split(";").map(c => c.trim()).filter(c => c.startsWith("atlas_session="));
  if (cookies.length > 1 || (cookies[0] && !/^atlas_session=(?:[A-Za-z0-9_-]{0,100}|"")$/.test(cookies[0]))) return error(400, "Invalid session cookie.");
  if (cookies[0]) headers.set("Cookie", cookies[0]);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const disconnect = () => controller.abort();
  request.signal.addEventListener("abort", disconnect, { once: true });
  if (request.signal.aborted) controller.abort();
  try {
    let body;
    try { body = await readBounded(request.body, 65536, controller.signal); }
    catch (reason) { if (reason instanceof RangeError) return error(413, "Request exceeds 64 KiB."); throw reason; }
    const upstream = await fetcher(settings.upstream + url.pathname + url.search, {
      method: request.method, headers, body, redirect: "manual", cache: "no-store", signal: controller.signal,
    });
    if ((upstream.status >= 300 && upstream.status < 400) || upstream.status >= 500 ||
      (upstream.status !== 204 && !/^application\/json(?:\s*;|$)/i.test(upstream.headers.get("Content-Type") ?? ""))) {
      void upstream.body?.cancel().catch(() => {});
      return error(503, "The demo server may be waking up. Wait a minute and retry manually. Do not resubmit an uncertain account action.");
    }
    const output = new Headers({ "Cache-Control": "no-store", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer" });
    const contentType = upstream.headers.get("Content-Type");
    if (contentType) output.set("Content-Type", contentType);
    const retry = upstream.headers.get("Retry-After");
    if (retry && /^\d{1,3}$/.test(retry)) output.set("Retry-After", retry);
    for (const value of upstream.headers.getSetCookie()) {
      if (!safeCookie(value)) { void upstream.body?.cancel().catch(() => {}); return error(503, "Incompatible demo session response."); }
      output.append("Set-Cookie", value);
    }
    return new Response(await readBounded(upstream.body, 2 * 1024 * 1024, controller.signal), { status: upstream.status, headers: output });
  } catch {
    return error(503, "The demo server is unavailable or waking up. Retry manually after a minute; account actions are never retried automatically.");
  } finally { clearTimeout(timer); request.signal.removeEventListener("abort", disconnect); }
}
export async function configuredProxy(request: Request): Promise<Response> {
  if (process.env.NEXT_PUBLIC_ATLAS_OFFLINE_DEMO === "true")
    return Response.json({ error: { message: "API and account access are disabled in this offline demo." } }, { status: 404, headers: { "Cache-Control": "no-store" } });
  try { return await proxyRequest(request, proxySettings(process.env)); }
  catch { return error(503, "The demo API is not configured safely."); }
}
