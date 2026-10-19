import { z } from "zod";
import { apiRequest, queryParams } from "./api-client";
import { apiBaseUrl } from "./config";

const nullableText = z.string().nullable();
const quoted = z.string().regex(/^\d+(\.\d+)?$/).nullable();
const benefit = z.object({
  kind: z.enum(["tuition_waiver", "stipend", "accommodation", "insurance", "travel", "other"]),
  label: z.string(), coverage_mode: z.enum(["fixed", "percentage", "full_eligible_cost", "in_kind", "unknown"]),
  value_state: z.enum(["unknown", "estimated", "confirmed"]),
  condition_state: z.enum(["unknown", "conditional", "unconditional"]),
  delivery_mode: z.string(), amount: quoted, cap_amount: quoted, percent: quoted,
  currency: nullableText, period: nullableText, eligible_cost_basis: nullableText,
  payment_months: z.number().nullable(), coverage_months: z.number().nullable(),
  conditions: nullableText, renewal_terms: nullableText, stacking_terms: nullableText,
  recipient_limit: z.number().nullable(),
});
export const scholarshipV2Schema = z.object({
  id: z.string(), contract_version: z.literal(2), name: z.string(), provider: z.string(),
  description: z.string(), eligibility_summary: z.string(), coverage: z.string(),
  official_url: nullableText, funding_type: z.enum(["Full", "Partial"]).nullable(),
  scheme_key: nullableText, round_key: nullableText, cycle_state: z.enum(["known", "unknown"]),
  intake_label: nullableText, academic_cycle: nullableText, intake_start_date: nullableText,
  provider_kind: nullableText, applicability_state: z.enum(["listed", "unknown", "unrestricted"]),
  benefits: z.record(z.string(), benefit).nullable(),
  requirements: z.record(z.string(), z.object({
    category: z.string(), statement: z.string(), applies_to_country_codes: z.array(z.string()).nullable(),
    nationality_mode: z.enum(["unknown", "unrestricted", "allowlist", "denylist"]),
    nationality_codes: z.array(z.string()), conditions: nullableText,
  })).nullable(),
  deadlines: z.record(z.string(), z.object({
    stage: z.string(), date: nullableText, closes_at: nullableText, timezone: nullableText,
    deadline_state: z.enum(["known", "rolling", "unknown"]), conditions: nullableText,
  })).nullable(),
  scopes: z.array(z.object({id: z.string(), country_id: nullableText, university_id: nullableText,
    program_id: nullableText, degree_level: nullableText, scope_extent: z.enum(["exact_target", "descendants"])})),
  scope_labels: z.record(z.string(), z.string()), verification_status: z.literal("verified"),
  evidence: z.array(z.object({ field: z.string(), source: z.object({
    id: z.string(), source_type: z.string(), title: z.string(), source_url: nullableText,
    publisher: z.string(), retrieved_at: nullableText,
  })})),
});
export type ScholarshipV2 = z.infer<typeof scholarshipV2Schema>;
export const scholarshipPageSchema = z.object({ items: z.array(scholarshipV2Schema),
  meta: z.object({page: z.number(), page_size: z.number(), total: z.number(), pages: z.number()}) });
const base = new URL("../v2", apiBaseUrl + "/").href.replace(/\/$/, "");
export function scholarshipList(filters: Record<string, string | number>, fetcher: typeof fetch = fetch) {
  return apiRequest("/scholarships", scholarshipPageSchema, queryParams(filters), fetcher, 8000, base);
}
export function scholarshipDetail(id: string, fetcher: typeof fetch = fetch) {
  return apiRequest("/scholarships/" + encodeURIComponent(id), scholarshipV2Schema, undefined, fetcher, 8000, base);
}
export function safeScholarshipLink(value: string | null) {
  if (!value || /[\s\\\x00-\x1f\x7f]/.test(value)) return null;
  try { const u = new URL(value); return ["https:", "http:"].includes(u.protocol) && !u.username && !u.password ? value : null; }
  catch { return null; }
}
export function benefitQuotation(b: z.infer<typeof benefit>) {
  const qualifier = b.value_state === "estimated" ? "Estimate: " : "Published term: ";
  if (b.value_state === "unknown" || b.coverage_mode === "unknown") return "Amount unknown";
  if (b.coverage_mode === "fixed") return qualifier + `${b.amount ?? "Unknown"} ${b.currency ?? "currency unknown"} / ${b.period ?? "period unknown"}`;
  if (b.coverage_mode === "percentage") return qualifier + `${b.percent ?? "Unknown"}% of ${b.eligible_cost_basis ?? "eligible basis unknown"}`;
  if (b.coverage_mode === "full_eligible_cost") return qualifier + `eligible ${b.eligible_cost_basis ?? "costs"} covered`;
  return "Published in-kind benefit; cash value unknown";
}
