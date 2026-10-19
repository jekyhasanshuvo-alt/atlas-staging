import { profileSchema } from "@/lib/validation/profile";
import { financialPlanSchema } from "@/lib/validation/financial-plan";
import { toProfile } from "./student";

export function collectLocalImport(storage: Pick<Storage, "getItem">) {
  const skipped: string[] = [];
  const payload: Record<string, unknown> = { import_version: 1 };
  function read(key: string): unknown {
    try {
      const raw = storage.getItem(key);
      return raw === null ? undefined : JSON.parse(raw);
    } catch {
      skipped.push(key + ": invalid stored JSON");
      return undefined;
    }
  }
  const profile = read("student-profile");
  if (profile !== undefined) {
    const parsed = profileSchema.strict().safeParse(profile);
    if (parsed.success) payload.profile = toProfile(parsed.data);
    else skipped.push("student-profile: invalid preferences");
  }
  for (const [key, field] of [
    ["saved-universities", "universities"],
    ["saved-scholarships", "scholarships"],
    ["comparison", "comparison"],
  ]) {
    const value = read(key);
    if (value === undefined) continue;
    if (
      Array.isArray(value) &&
      value.length <= (field === "comparison" ? 4 : 100) &&
      value.every((v) => typeof v === "string" && v.length <= 120)
    )
      payload[field] =
        field === "comparison"
          ? { ids: [...new Set(value)] }
          : [...new Set(value)];
    else skipped.push(key + ": invalid IDs or too many items");
  }
  const plan = read("financial-plan"),
    baseline = read("financial-scenario");
  if (plan !== undefined) {
    const parsed = financialPlanSchema.strict().safeParse(plan);
    if (parsed.success) {
      const b = financialPlanSchema.strict().safeParse(baseline);
      payload.financial_plan = {
        ...parsed.data,
        name: "Imported browser plan",
        baseline: b.success ? b.data : null,
      };
      if (baseline != null && !b.success)
        skipped.push("financial-scenario: invalid baseline");
    } else skipped.push("financial-plan: invalid plan");
  }
  const allowed: Record<string, string[]> = {
    preparation: ["profile", "shortlist", "funding", "documents"],
    "life-checklist": [
      "passport",
      "arrival",
      "housing",
      "transport",
      "banking",
      "health",
    ],
    "career-checklist": ["explore", "skills", "cv", "internship", "pathways"],
  };
  const checklists = [];
  for (const [category, keys] of Object.entries(allowed)) {
    const value = read(category);
    if (value === undefined) continue;
    if (
      Array.isArray(value) &&
      value.every((v) => typeof v === "string" && keys.includes(v))
    )
      checklists.push({ category, completed: [...new Set(value)] });
    else skipped.push(category + ": unknown task keys");
  }
  payload.checklists = checklists;
  return { payload, skipped };
}
