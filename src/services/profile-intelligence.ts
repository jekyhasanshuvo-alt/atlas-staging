import { z } from "zod";
import { intelligenceSchema } from "./intelligence";
import { statusSchema } from "./contracts";
const text = z.string().nullable();
const evidence = z.object({ evidence_reference: z.string(), verification_status: statusSchema, reviewed_at: text,
    source: z.object({ id: z.string(), source_type: z.string(), title: z.string(), source_url: text, publisher: z.string(), retrieved_at: text }) });
export const completenessSchema = z.object({ provided: z.number().int().nonnegative(), supported: z.number().int().nonnegative(),
    dimensions: z.array(z.object({ field: z.string(), label: z.string(), status: z.enum(["PROVIDED", "MISSING", "UNSUPPORTED"]), explanation: z.string() })), explanation: z.string() });
const reason = z.object({ attribute: z.string(), outcome: z.enum(["MATCH", "DIFFERENT", "UNKNOWN", "NOT_SET"]), input_used: text, program_value: text,
    logic: z.string(), uncertainty: z.string(), catalog_verification: statusSchema, evidence: z.array(evidence) });
export const matchSchema = z.object({ program: intelligenceSchema, preference_result: z.enum(["MATCHES", "DIFFERS", "UNKNOWN"]), reasons: z.array(reason),
    eligibility_status: z.literal("NOT_ASSESSED"), explanation: z.string() });
export const matchPageSchema = z.object({ items: z.array(matchSchema), meta: z.object({ page: z.number(), page_size: z.number(), total: z.number(), pages: z.number() }), explanation: z.string() });
export const assessmentSchema = matchSchema.extend({ eligibility_checks: z.array(z.object({ category: z.string(),
        status: z.literal("NOT_ASSESSED"), requirement: z.string(), student_input_used: z.record(z.string(), text),
        official_requirement_source: z.null(), comparison_logic: z.string(), uncertainty: z.string() })) });
export type Completeness = z.infer<typeof completenessSchema>;
export type ProgramMatch = z.infer<typeof matchSchema>;
export type ProgramAssessment = z.infer<typeof assessmentSchema>;
export type Requester = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
export type AssessmentOptions = {
    preferred_degree?: "Bachelor" | "Master" | "PhD";
    teaching_language?: string;
    budget_period?: "year" | "semester" | "month" | "degree";
};
export type MatchingOptions = AssessmentOptions & {
    q?: string;
    university?: string;
    verification?: string;
    preference_result?: string;
    page?: number;
    page_size?: number;
};
async function request<T>(send: Requester, path: string, schema: z.ZodType<T>, body?: unknown): Promise<T> {
    const data = await send<unknown>(path, body === undefined ? "GET" : "POST", body), parsed = schema.safeParse(data);
    if (!parsed.success)
        throw new Error("The account server returned an incompatible intelligence response. Please retry.");
    return parsed.data;
}
export function profileCompleteness(send: Requester) { return request(send, "/me/intelligence/completeness", completenessSchema); }
export function programMatches(send: Requester, options: MatchingOptions) { return request(send, "/me/intelligence/matches", matchPageSchema, options); }
export function programAssessment(send: Requester, id: string, options: AssessmentOptions) { return request(send, "/me/intelligence/assessments/" + encodeURIComponent(id), assessmentSchema, options); }
export function preferenceLabel(result: ProgramMatch["preference_result"]) { return result === "MATCHES" ? "Stored preferences match" : result === "DIFFERS" ? "Stored preferences differ" : "Preference comparison unknown"; }
