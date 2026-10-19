import { z } from "zod";
import { apiRequest, queryParams } from "./api-client";
import { apiBaseUrl } from "./config";
import { countrySchema, statusSchema } from "./contracts";
const text = z.string().nullable();
export const intelligenceSchema = z.object({
    id: z.string(), kind: z.enum(["university", "program"]), name: z.string(), country: countrySchema,
    city: z.object({ id: z.string(), name: z.string(), country_id: z.string() }), is_demo: z.boolean(), verification_status: statusSchema,
    facts: z.record(z.string(), z.object({ value: z.union([z.string(), z.number()]).nullable(), verification_status: statusSchema, caveat: z.string(),
        evidence: z.array(z.object({ evidence_reference: z.string(), verification_status: statusSchema, reviewed_at: text,
            source: z.object({ id: z.string(), source_type: z.string(), title: z.string(), source_url: text, publisher: z.string(), retrieved_at: text }) })) })),
    university_id: text, university_name: text, degree_level: text, field_of_study: text, language_of_instruction: text,
    duration_months: z.number().int().positive().nullable(), tuition_amount: z.string().regex(/^\d+(\.\d+)?$/).nullable(),
    tuition_currency: text, tuition_period: text, institution_type: text, official_website: text, description: text,
});
export type Intelligence = z.infer<typeof intelligenceSchema>;
export type CatalogKind = "universities" | "programs";
export const intelligencePageSchema = z.object({ items: z.array(intelligenceSchema), meta: z.object({ page: z.number(), page_size: z.number(), total: z.number(), pages: z.number() }) });
export const comparisonSchema = z.object({ items: z.array(intelligenceSchema), unavailable_ids: z.array(z.string()) });
const base = new URL("../v2/intelligence", apiBaseUrl + "/").href.replace(/\/$/, "");
export function intelligenceList(kind: CatalogKind, filters: Record<string, string | number>, fetcher: typeof fetch = fetch) { return apiRequest("/" + kind, intelligencePageSchema, queryParams(filters), fetcher, 8000, base); }
export function intelligenceDetail(kind: CatalogKind, id: string, fetcher: typeof fetch = fetch) { return apiRequest("/" + kind + "/" + encodeURIComponent(id), intelligenceSchema, undefined, fetcher, 8000, base); }
export function intelligenceCompare(kind: CatalogKind, ids: string[], fetcher: typeof fetch = fetch) { return apiRequest("/compare/" + kind, comparisonSchema, queryParams({ ids }), fetcher, 8000, base); }
export function tuitionQuote(item: Intelligence) { return item.tuition_amount === null ? "Tuition unknown" : `${item.tuition_amount} ${item.tuition_currency ?? "currency unknown"} / ${item.tuition_period ?? "period unknown"}`; }
export function comparisonSelection(previous: string[], id: string) { return previous.includes(id) ? previous.filter(v => v !== id) : previous.length < 4 ? [...previous, id] : previous; }
