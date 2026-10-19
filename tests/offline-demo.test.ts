import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import { z } from "zod";

const route = vi.hoisted(() => {
  process.env.NEXT_PUBLIC_ATLAS_OFFLINE_DEMO = "true";
  process.env.NEXT_PUBLIC_ATLAS_DATA_MODE = "demo";
  process.env.NEXT_PUBLIC_ATLAS_STAGING_DEMO = "false";
  return { path: "/" };
});
vi.mock("next/navigation", () => ({ usePathname: () => route.path }));
import { OfflineDemoBoundary } from "@/components/offline-demo-boundary";
import { studentRequest } from "@/services/student";
import { apiRequest } from "@/services/api-client";
import { configuredProxy } from "@/server/staging-proxy";
import { demoRepository } from "@/services/repository";
import { defaultPlan } from "@/data/mock";
import { calculateBudget } from "@/lib/calculations/finance";

afterEach(() => vi.unstubAllGlobals());

it.each(["/signup", "/login", "/verify-email", "/forgot-password", "/reset-password", "/profile", "/onboarding", "/settings", "/assistant", "/advisor", "/applications/new"])("never mounts data collection at %s", (path) => {
  route.path = path;
  const html = renderToStaticMarkup(createElement(OfflineDemoBoundary, null, createElement("form", null, createElement("input", { name: "email" }))));
  expect(html).toContain("Unavailable in this public demo");
  expect(html).not.toContain("<form");
  expect(html).not.toContain("<input");
});

it("labels allowed demo screens and renders their content", () => {
  route.path = "/financial-twin";
  const html = renderToStaticMarkup(createElement(OfflineDemoBoundary, null, "HYPOTHETICAL CALCULATOR"));
  expect(html).toContain("DEMO ONLY");
  expect(html).toContain("HYPOTHETICAL CALCULATOR");
  expect(html).toContain("Inputs reset on reload");
});

it("blocks all configured API proxy paths even if an upstream is configured", async () => {
  const fetcher = vi.fn(() => { throw new Error("No outbound request permitted"); });
  vi.stubGlobal("fetch", fetcher);
  for (const path of ["/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/me/profile", "/api/v1/health", "/api/v2/scholarships"]) {
    const response = await configuredProxy(new Request("https://demo.invalid" + path, { method: "POST" }));
    expect(response.status).toBe(404);
    expect(response.headers.get("set-cookie")).toBeNull();
  }
  expect(fetcher).not.toHaveBeenCalled();
});

it("blocks direct account and API clients before fetch", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  await expect(studentRequest("/auth/register", "POST", {})).rejects.toThrow("disabled");
  await expect(apiRequest("/countries", z.unknown())).rejects.toThrow("disabled");
  expect(fetcher).not.toHaveBeenCalled();
});

it("contains no institutional or award fixtures", () => {
  expect(demoRepository.getUniversities()).toEqual([]);
  expect(demoRepository.getScholarships()).toEqual([]);
});

it("calculates the same hypothetical budget and clamps excess support", () => {
  const example = { ...defaultPlan, years: 2, tuition: 10000, accommodation: 1000, food: 300, transportation: 100, other: 100, insurance: 500, scholarship: 2000, relocation: 1000, emergency: 500 };
  const result = calculateBudget(example);
  expect(result).toEqual({ monthly: 1500, annual: 28500, total: 58500, funding: 4000, adjusted: 54500 });
  expect(calculateBudget(example)).toEqual(result);
  expect(calculateBudget({ ...example, scholarship: 100000 }).adjusted).toBe(0);
});
