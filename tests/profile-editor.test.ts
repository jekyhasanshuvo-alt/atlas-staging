import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, expect, it, vi } from "vitest";
import { CloudProfileEditor } from "@/features/auth/profile-editor";
import type { CloudProfile } from "@/services/student";

const state = vi.hoisted(() => ({
  workspace: null as null | { profile: CloudProfile },
  loading: false,
}));
vi.mock("@/components/auth/student-provider", () => ({
  useStudent: () => state,
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/components/shared", () => ({ PageHeader: () => null }));
beforeEach(() => {
  state.workspace = null;
  state.loading = false;
});

it.each([false, true])("prerenders without a workspace (onboarding=%s)", (onboarding) => {
  const html = renderToStaticMarkup(createElement(CloudProfileEditor, { onboarding }));
  expect(html).toContain("Your account profile is unavailable");
  expect(html).not.toContain("<form");
});

it("shows loading without mounting an empty editor", () => {
  state.loading = true;
  const html = renderToStaticMarkup(createElement(CloudProfileEditor));
  expect(html).toContain("Loading your account profile");
  expect(html).not.toContain("<form");
});

it("renders the supplied profile and resumes at the first incomplete step", () => {
  state.workspace = { profile: {
    full_name: "Fictional Student", nationality: "Bangladesh", current_country: "Bangladesh",
    education_level: "", academic_background: "", preferred_destination: "",
    budget_amount: "0", budget_currency: "BDT", scholarship_preference: false,
    preferred_subject: "", language_proficiency: "", career_goals: "",
    onboarding_completed_at: null,
  } as CloudProfile };
  const html = renderToStaticMarkup(createElement(CloudProfileEditor, { onboarding: true }));
  expect(html).toContain("<form");
  expect(html).toContain('aria-label="Current education level"');
  expect(html).toContain('aria-current="step"');
  expect(html).not.toContain("Your account profile is unavailable");
});
